"""Busca de matrícula em uma secretaria acadêmica.

Três estratégias: busca linear O(n), busca binária O(log n) e hash O(1) médio.
Inclui um pequeno benchmark para visualizar a diferença prática.
"""

from __future__ import annotations

import random
import time


# ---------------------------------------------------------------------------
# Implementações
# ---------------------------------------------------------------------------

def busca_linear(lista: list[int], alvo: int) -> bool:
    """Percorre a lista item por item. Complexidade: O(n)."""
    for item in lista:
        if item == alvo:
            return True
    return False


def busca_binaria(lista: list[int], alvo: int) -> bool:
    """Divide o espaço de busca pela metade. Exige lista ordenada.

    Complexidade da ordenação: O(n log n).
    Complexidade da busca:    O(log n).
    """
    lista_ord = sorted(lista)
    inicio, fim = 0, len(lista_ord) - 1
    while inicio <= fim:
        meio = (inicio + fim) // 2
        if lista_ord[meio] == alvo:
            return True
        if alvo < lista_ord[meio]:
            fim = meio - 1
        else:
            inicio = meio + 1
    return False


def busca_hash(lista: list[int], alvo: int) -> bool:
    """Consulta em estrutura hash (set).

    Complexidade da construção: O(n).
    Complexidade da consulta:   O(1) em média.
    """
    return alvo in set(lista)


# ---------------------------------------------------------------------------
# Demonstração com o enunciado
# ---------------------------------------------------------------------------

def demonstracao_enunciado() -> None:
    lista = [2023001, 2023045, 2023102, 2023120, 2023201, 2023333]
    alvo = 2023102
    nao_existe = 2024999

    print("=" * 60)
    print(f"Lista:     {lista}")
    print(f"Procurar:  {alvo} (esperado: True)")
    print("=" * 60)
    print(f"  busca_linear  -> {busca_linear(lista, alvo)}")
    print(f"  busca_binaria -> {busca_binaria(lista, alvo)}")
    print(f"  busca_hash    -> {busca_hash(lista, alvo)}")
    print()
    print(f"Procurar:  {nao_existe} (esperado: False)")
    print(f"  busca_linear  -> {busca_linear(lista, nao_existe)}")
    print(f"  busca_binaria -> {busca_binaria(lista, nao_existe)}")
    print(f"  busca_hash    -> {busca_hash(lista, nao_existe)}")


# ---------------------------------------------------------------------------
# Benchmark prático
# ---------------------------------------------------------------------------

def _cronometrar(func, *args) -> tuple[bool, float]:
    inicio = time.perf_counter()
    resultado = func(*args)
    fim = time.perf_counter()
    return resultado, (fim - inicio) * 1000  # ms


def benchmark(n: int = 100_000, consultas: int = 500) -> None:
    """Mede o tempo das 3 estratégias em uma lista de tamanho `n`."""
    print()
    print("=" * 60)
    print(f"Benchmark: lista com {n:,} matrículas, {consultas} consultas")
    print("=" * 60)

    random.seed(42)
    lista = random.sample(range(2_000_000, 9_999_999), n)
    alvos = random.sample(lista, consultas)  # alvos garantidamente presentes

    # Linear: faz tudo do zero a cada consulta.
    t0 = time.perf_counter()
    for alvo in alvos:
        busca_linear(lista, alvo)
    t_linear = (time.perf_counter() - t0) * 1000

    # Binária: ordena 1 vez fora do loop (custo amortizado nas consultas).
    t0 = time.perf_counter()
    lista_ord = sorted(lista)
    for alvo in alvos:
        inicio, fim = 0, len(lista_ord) - 1
        while inicio <= fim:
            meio = (inicio + fim) // 2
            if lista_ord[meio] == alvo:
                break
            if alvo < lista_ord[meio]:
                fim = meio - 1
            else:
                inicio = meio + 1
    t_binaria = (time.perf_counter() - t0) * 1000

    # Hash: constrói 1 vez fora do loop.
    t0 = time.perf_counter()
    conjunto = set(lista)
    for alvo in alvos:
        _ = alvo in conjunto
    t_hash = (time.perf_counter() - t0) * 1000

    print(f"  Linear  : {t_linear:>8.2f} ms")
    print(f"  Binária : {t_binaria:>8.2f} ms  (inclui ordenação inicial)")
    print(f"  Hash    : {t_hash:>8.2f} ms  (inclui construção do set)")
    print()
    print("Observe a relação:")
    print(f"  Linear / Hash    ≈ {t_linear / t_hash:.0f}x")
    print(f"  Linear / Binária ≈ {t_linear / t_binaria:.0f}x")


if __name__ == "__main__":
    demonstracao_enunciado()
    benchmark()
