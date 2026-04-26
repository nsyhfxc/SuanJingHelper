from __future__ import annotations

from dataclasses import dataclass
from math import comb, factorial, gcd, isqrt, log2, sqrt
import random


@dataclass(frozen=True)
class ComplexityRow:
    name: str
    operations: float
    verdict: str


def human_number(value: float | int) -> str:
    if value == float("inf"):
        return "∞"
    if isinstance(value, float) and value >= 1e18:
        return f"{value:.3e}"
    number = int(value) if float(value).is_integer() else value
    if abs(float(number)) >= 10000:
        return f"{float(number):,.0f}"
    if isinstance(number, float):
        return f"{number:.3g}"
    return f"{number:,}"


def estimate_complexities(n: float, cases: int, time_limit: float, ops_per_second: float) -> tuple[list[ComplexityRow], float]:
    budget = time_limit * ops_per_second
    total_cases = max(1, cases)
    values = [
        ("O(log N)", _safe_log(n)),
        ("O(sqrt N)", sqrt(n)),
        ("O(N)", n),
        ("O(N log N)", n * _safe_log(n)),
        ("O(N sqrt N)", n * sqrt(n)),
        ("O(N^2)", _safe_power(n, 2)),
        ("O(N^3)", _safe_power(n, 3)),
        ("O(2^N)", _safe_exp2(n)),
        ("O(N!)", _safe_factorial(n)),
    ]
    rows = [
        ComplexityRow(name, operations * total_cases, _complexity_verdict(operations * total_cases, budget))
        for name, operations in values
    ]
    return rows, budget


def max_n_table(cases: int, time_limit: float, ops_per_second: float) -> list[tuple[str, str]]:
    per_case_budget = max(1.0, time_limit * ops_per_second / max(1, cases))
    return [
        ("O(N)", human_number(per_case_budget)),
        ("O(N log N)", human_number(_max_n_binary(lambda x: x * _safe_log(x), per_case_budget))),
        ("O(N sqrt N)", human_number(_max_n_binary(lambda x: x * sqrt(x), per_case_budget))),
        ("O(N^2)", human_number(isqrt(int(per_case_budget)))),
        ("O(N^3)", human_number(int(per_case_budget ** (1 / 3)))),
        ("O(2^N)", human_number(int(log2(per_case_budget)) if per_case_budget >= 1 else 0)),
        ("O(N!)", human_number(_max_factorial_n(per_case_budget))),
    ]


def extended_gcd(a: int, b: int) -> tuple[int, int, int]:
    old_r, r = abs(a), abs(b)
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    x = old_s if a >= 0 else -old_s
    y = old_t if b >= 0 else -old_t
    return old_r, x, y


def mod_inverse(a: int, mod: int) -> int | None:
    if mod <= 1:
        return None
    g, x, _ = extended_gcd(a, mod)
    if g != 1:
        return None
    return x % mod


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small_primes:
        if n % p == 0:
            return n == p

    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2

    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def factorize(n: int) -> dict[int, int]:
    n = abs(n)
    if n <= 1:
        return {}
    factors: list[int] = []
    _factor_recursive(n, factors)
    result: dict[int, int] = {}
    for item in factors:
        result[item] = result.get(item, 0) + 1
    return dict(sorted(result.items()))


def format_factorization(factors: dict[int, int]) -> str:
    if not factors:
        return "无"
    return " * ".join(f"{p}^{e}" if e > 1 else str(p) for p, e in factors.items())


def euler_phi(n: int) -> int:
    if n <= 0:
        raise ValueError("phi 只接受正整数")
    result = n
    for p in factorize(n):
        result = result // p * (p - 1)
    return result


def divisor_summary(n: int) -> tuple[int, int]:
    if n == 0:
        raise ValueError("0 的约数个数与约数和没有有限定义")
    factors = factorize(n)
    count = 1
    total = 1
    for p, exp in factors.items():
        count *= exp + 1
        total *= (p ** (exp + 1) - 1) // (p - 1)
    return count, total


def combination_exact(n: int, r: int, max_n: int = 5000) -> int | None:
    if n < 0 or r < 0 or r > n:
        return 0
    if n > max_n:
        return None
    return comb(n, r)


def permutation_exact(n: int, r: int, max_n: int = 5000) -> int | None:
    if n < 0 or r < 0 or r > n:
        return 0
    if n > max_n:
        return None
    return factorial(n) // factorial(n - r)


def comb_mod_prime(n: int, r: int, mod: int, loop_limit: int = 200000) -> int | None:
    if mod <= 1 or not is_prime(mod):
        return None
    if r < 0 or r > n:
        return 0
    result = 1
    while n or r:
        ni, ri = n % mod, r % mod
        if ri > ni:
            return 0
        if min(ri, ni - ri) > loop_limit:
            return None
        result = result * _comb_small_prime_mod(ni, ri, mod) % mod
        n //= mod
        r //= mod
    return result


def permutation_mod_prime(n: int, r: int, mod: int, loop_limit: int = 200000) -> int | None:
    if mod <= 1 or not is_prime(mod):
        return None
    if r < 0 or r > n:
        return 0
    if r > loop_limit:
        return None
    result = 1
    for value in range(n - r + 1, n + 1):
        result = result * (value % mod) % mod
    return result


def bit_summary(x: int) -> list[tuple[str, str]]:
    absolute = abs(x)
    if x >= 0:
        binary = bin(x)
        hexa = hex(x)
    else:
        binary = "-" + bin(absolute)
        hexa = "-" + hex(absolute)

    rows = [
        ("二进制", binary),
        ("十六进制", hexa),
        ("bit_length", str(absolute.bit_length())),
        ("popcount", str(absolute.bit_count())),
    ]
    if absolute == 0:
        rows.extend(
            [
                ("lowbit", "0"),
                ("floor(log2)", "无"),
                ("最高 2^k", "0"),
                ("下一个 2^k", "1"),
                ("是否 2 的幂", "否"),
            ]
        )
        return rows

    lowbit = absolute & -absolute
    highest = 1 << (absolute.bit_length() - 1)
    next_power = highest if absolute == highest else highest << 1
    rows.extend(
        [
            ("lowbit", str(lowbit)),
            ("floor(log2)", str(absolute.bit_length() - 1)),
            ("最高 2^k", str(highest)),
            ("下一个 2^k", str(next_power)),
            ("是否 2 的幂", "是" if absolute == highest else "否"),
        ]
    )
    return rows


def _safe_log(n: float) -> float:
    return log2(max(2.0, n))


def _safe_power(n: float, power: int) -> float:
    if n > 1e100:
        return float("inf")
    return n**power


def _safe_exp2(n: float) -> float:
    if n > 1024:
        return float("inf")
    return 2**n


def _safe_factorial(n: float) -> float:
    if n > 170:
        return float("inf")
    if n < 0:
        return float("inf")
    return float(factorial(int(n)))


def _complexity_verdict(operations: float, budget: float) -> str:
    if operations <= budget * 0.35:
        return "稳"
    if operations <= budget:
        return "可过"
    if operations <= budget * 3:
        return "偏险"
    return "超时"


def _max_n_binary(func, budget: float) -> int:
    low, high = 1, 2
    while func(high) <= budget and high < 10**18:
        high *= 2
    while low < high:
        mid = (low + high + 1) // 2
        if func(mid) <= budget:
            low = mid
        else:
            high = mid - 1
    return low


def _max_factorial_n(budget: float) -> int:
    value = 1
    n = 1
    while value * (n + 1) <= budget:
        n += 1
        value *= n
    return n


def _factor_recursive(n: int, factors: list[int]) -> None:
    if n == 1:
        return
    if is_prime(n):
        factors.append(n)
        return
    divisor = _pollard_rho(n)
    _factor_recursive(divisor, factors)
    _factor_recursive(n // divisor, factors)


def _pollard_rho(n: int) -> int:
    if n % 2 == 0:
        return 2
    if n % 3 == 0:
        return 3

    while True:
        c = random.randrange(1, n - 1)
        x = random.randrange(0, n - 1)
        y = x
        d = 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = gcd(abs(x - y), n)
        if d != n:
            return d


def _comb_small_prime_mod(n: int, r: int, mod: int) -> int:
    r = min(r, n - r)
    result = 1
    for i in range(1, r + 1):
        result = result * ((n - r + i) % mod) % mod
        result = result * pow(i, mod - 2, mod) % mod
    return result
