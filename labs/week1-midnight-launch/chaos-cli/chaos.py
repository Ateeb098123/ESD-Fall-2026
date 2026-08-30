#!/usr/bin/env python3
"""
Game Day Chaos CLI Tool — Midnight Ticketmaster Launch SRE Lab
Language: Python 3
"""

import argparse
import threading
import time
from collections import Counter as Tally
from concurrent.futures import ThreadPoolExecutor, wait

import requests

GATEWAY_URL = "http://localhost:8080"
INVENTORY_URL = "http://localhost:8081"
PAYMENT_URL = "http://localhost:8082"

# One Session per worker thread. requests.Session is not documented as
# thread-safe, so sharing a single Session across a pool can corrupt
# connection state under load.
_local = threading.local()


def _session():
    s = getattr(_local, "session", None)
    if s is None:
        s = _local.session = requests.Session()
    return s


def print_banner():
    print("=" * 60)
    print(" 🚨 MIDNIGHT TICKETMASTER LAUNCH — GAME DAY CHAOS CLI 🚨")
    print("=" * 60)


def status():
    print_banner()
    try:
        gw = requests.get(f"{GATEWAY_URL}/chaos/status", timeout=2).json()
        inv = requests.get(f"{INVENTORY_URL}/chaos/status", timeout=2).json()
        pay = requests.get(f"{PAYMENT_URL}/chaos/status", timeout=2).json()

        print("\n[ACTIVE CHAOS STATUS]")
        print(f" • API Gateway Circuit Breaker : {gw.get('circuit_breaker')} (Enabled: {gw.get('circuit_breaker_enabled')})")
        print(f" • Cardinality Bomb            : {'ACTIVE 💣 (%d distinct series)' % gw.get('cardinality_users_count', 0) if gw.get('cardinality_bomb') else 'OFF'}")
        print(f" • Fan-Out Dependencies (N)    : {gw.get('fanout_n', 0)}")
        print(f" • Postgres DB Lock Delay      : {'LOCKED 🔒 (%.0fms)' % (inv.get('lock_delay_seconds', 3) * 1000) if inv.get('db_locked') else 'OFF (Normal)'}")
        print(f" • Dependency Tail Probability : p={inv.get('tail_probability', 0.01)} (delay {inv.get('tail_delay_seconds', 1.0)}s)")
        print(f" • Payment Third-Party RateLmt : {'ACTIVE ⚠️ (%.0f%% 429s)' % (pay.get('error_rate_pct', 0.4) * 100) if pay.get('rate_limit_active') else 'OFF (Normal)'}\n")
    except Exception as e:
        print(f"\n❌ Error connecting to microservices: {e}")
        print("   Make sure services are running: docker compose up -d\n")


def send_request():
    try:
        res = _session().post(f"{GATEWAY_URL}/checkout", timeout=15)
        return res.status_code
    except Exception:
        return 0  # 0 == client-side timeout / connection failure


def load_generator(rps, duration, drain=20):
    """
    Open-loop load generator: requests are submitted on a wall-clock schedule
    rather than waiting for the previous batch to drain. A closed-loop generator
    (submit N, block on all N, sleep) silently reduces its own arrival rate as
    the system slows down, which hides the very queueing effect the lab teaches.

    Achieved RPS is measured and reported — if the system cannot keep up, that
    gap IS the finding, so it is printed rather than hidden.
    """
    print_banner()
    print(f"🚀 Starting Traffic Surge: Target {rps} RPS for {duration}s (open-loop)...")

    total = rps * duration
    # Concurrency ceiling. Little's Law: sustaining λ with latency W needs
    # L = λW in-flight. We cap threads to keep the client from OOMing the
    # student's laptop; hitting the cap is itself a saturation signal.
    workers = min(max(50, rps), 600)
    futures = []
    start = time.time()
    executor = ThreadPoolExecutor(max_workers=workers)

    try:
        submitted = 0
        while submitted < total:
            elapsed = time.time() - start
            if elapsed >= duration:
                break
            # How many should have been sent by now on a uniform schedule?
            target = min(total, int(elapsed * rps) + 1)
            while submitted < target:
                futures.append(executor.submit(send_request))
                submitted += 1
            time.sleep(0.002)

        send_window = time.time() - start
        print(f"   submitted {submitted} requests in {send_window:.1f}s, draining (max {drain}s)...")

        # Bounded drain. A saturated system can hold thousands of requests in
        # queue; blocking until every one resolves turns a 10s surge into a
        # multi-minute terminal freeze. Abandon the stragglers and count them.
        done, pending = wait(futures, timeout=drain)
        for f in pending:
            f.cancel()
        tally = Tally(f.result() for f in done)
        abandoned = len(pending)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    wall = time.time() - start
    completed = sum(tally.values())
    ok = tally.get(200, 0)
    achieved = completed / wall if wall else 0

    print(f"\n✅ Load Surge Finished in {wall:.1f}s")
    print(f"   submitted : {submitted} / {total} scheduled")
    print(f"   completed : {completed}  ({ok} OK, {completed - ok} failed)")
    if abandoned:
        print(f"   abandoned : {abandoned} still queued/in-flight when drain expired")
    print(f"   achieved  : {achieved:.0f} RPS vs {rps} RPS target ({achieved / rps * 100:.0f}%)")
    breakdown = ", ".join(f"{'timeout' if c == 0 else c}={n}" for c, n in sorted(tally.items()))
    print(f"   status    : {breakdown}")
    if achieved < rps * 0.9:
        print(f"   ⚠️  System could not absorb the target rate — this is saturation,")
        print(f"      not a broken load generator. Compare against Little's Law: L = λW.")


def _post(url, label, ok_msg, fail_msg):
    try:
        requests.post(url, timeout=5)
        print(ok_msg)
    except Exception as e:
        print(f"❌ Failed to reach {label}: {e}")


def trigger_db_lock(enable, delay=3.0):
    _post(f"{INVENTORY_URL}/chaos/db-lock?locked={'true' if enable else 'false'}&delay={delay}",
          "Inventory Service",
          f"🔒 Postgres Row-Lock Chaos: {'ACTIVATED (%.0fms latency injected)' % (delay * 1000) if enable else 'DEACTIVATED'}",
          "Inventory Service")


def trigger_rate_limit(enable, error_rate=0.40):
    _post(f"{PAYMENT_URL}/chaos/rate-limit?active={'true' if enable else 'false'}&error_rate={error_rate}",
          "Payment Service",
          f"⚠️ Third-Party Rate Limit Chaos: {'ACTIVATED (%.0f%% HTTP 429 errors)' % (error_rate * 100) if enable else 'DEACTIVATED'}",
          "Payment Service")


def trigger_cardinality(enable):
    _post(f"{GATEWAY_URL}/chaos/cardinality?active={'true' if enable else 'false'}",
          "API Gateway",
          f"💣 TSDB Cardinality Bomb: {'ACTIVATED (tagging user_id in metrics)' if enable else 'DEACTIVATED'}",
          "API Gateway")


def trigger_circuit_breaker(enable, state="OPEN"):
    _post(f"{GATEWAY_URL}/chaos/circuit-breaker?enabled={'true' if enable else 'false'}&state={state}",
          "API Gateway",
          f"⚡ API Gateway Circuit Breaker: {'ENABLED (' + state + ')' if enable else 'DISABLED'}",
          "API Gateway")


def trigger_fanout(n, probability):
    _post(f"{GATEWAY_URL}/chaos/fanout?n={n}", "API Gateway",
          f"🌐 Fan-Out Dependencies set to N={n}", "API Gateway")
    _post(f"{INVENTORY_URL}/chaos/tail?probability={probability}", "Inventory Service",
          f"   per-dependency tail probability p={probability}", "Inventory Service")
    if n > 0:
        predicted = 1 - (1 - probability) ** n
        print(f"   📐 Predicted P(request slow) = 1-(1-{probability})^{n} = {predicted * 100:.2f}%")


def reset_all():
    _post(f"{GATEWAY_URL}/chaos/reset", "API Gateway",
          "🧹 Reset All Chaos Injections: Telemetry normalized.", "API Gateway")


def main():
    parser = argparse.ArgumentParser(description="Midnight Launch SRE Chaos CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status")
    subparsers.add_parser("reset")

    load_parser = subparsers.add_parser("load")
    load_parser.add_argument("--rps", type=int, default=100, help="Target Requests Per Second")
    load_parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    load_parser.add_argument("--drain", type=int, default=20, help="Max seconds to wait for in-flight responses after the send window")

    db_parser = subparsers.add_parser("db-lock")
    db_parser.add_argument("--off", action="store_true", help="Disable DB lock")
    db_parser.add_argument("--delay", type=float, default=3.0, help="Lock delay in seconds")

    rl_parser = subparsers.add_parser("rate-limit")
    rl_parser.add_argument("--off", action="store_true", help="Disable rate limiting")
    rl_parser.add_argument("--error-rate", type=float, default=0.40, help="Fraction of requests rejected with 429")

    card_parser = subparsers.add_parser("cardinality-bomb")
    card_parser.add_argument("--off", action="store_true", help="Disable cardinality bomb")

    cb_parser = subparsers.add_parser("circuit-breaker")
    cb_parser.add_argument("--off", action="store_true", help="Disable circuit breaker")
    cb_parser.add_argument("--state", type=str, default="OPEN", choices=["CLOSED", "OPEN", "HALF-OPEN"])

    fan_parser = subparsers.add_parser("fanout")
    fan_parser.add_argument("--n", type=int, default=25, help="Number of parallel downstream dependencies")
    fan_parser.add_argument("--probability", type=float, default=0.01, help="Per-dependency tail probability p")
    fan_parser.add_argument("--off", action="store_true", help="Disable fan-out (N=0)")

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "load":
        load_generator(args.rps, args.duration, args.drain)
    elif args.command == "db-lock":
        trigger_db_lock(not args.off, args.delay)
    elif args.command == "rate-limit":
        trigger_rate_limit(not args.off, args.error_rate)
    elif args.command == "cardinality-bomb":
        trigger_cardinality(not args.off)
    elif args.command == "circuit-breaker":
        trigger_circuit_breaker(not args.off, args.state)
    elif args.command == "fanout":
        trigger_fanout(0 if args.off else args.n, args.probability)
    elif args.command == "reset":
        reset_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
