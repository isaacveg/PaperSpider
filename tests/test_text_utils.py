# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest

from paper_spider.text_utils import display_title


class DisplayTitleTests(unittest.TestCase):
    def test_renders_common_title_markup(self) -> None:
        cases = {
            "$C^2M^3$: Cycle-Consistent Multi-Model Merging": "C²M³: Cycle-Consistent Multi-Model Merging",
            "$E^3$: Exploring Embodied Emotion": "E³: Exploring Embodied Emotion",
            "$SE(3)$ Equivariant Ray Embeddings": "SE(3) Equivariant Ray Embeddings",
            "$\\beta$-DPO: Direct Preference Optimization": "β-DPO: Direct Preference Optimization",
            "$\\boldsymbol{\\mu}\\mathbf{P^2}$: Effective Sharpness": "μP²: Effective Sharpness",
            "$\\epsilon$-Softmax: Approximating One-Hot Vectors": "ε-Softmax: Approximating One-Hot Vectors",
            "$\\nabla^2$DFT: A Universal Quantum Chemistry Dataset": "∇²DFT: A Universal Quantum Chemistry Dataset",
            "$\\textit{Bifr\\\"ost}$: 3D-Aware Image Compositing": "Bifröst: 3D-Aware Image Compositing",
            "$\\textit{Read-ME}$: Refactorizing LLMs": "Read-ME: Refactorizing LLMs",
            "$\\texttt{ConflictBank}$: A Benchmark": "ConflictBank: A Benchmark",
            "$\\text{ID}^3$: Identity-Preserving": "ID³: Identity-Preserving",
            "Scaling $O(n \\log n)$ Attention": "Scaling O(n log n) Attention",
            "Learning in $\\ell_2$ and $x_{t+1}$": "Learning in ℓ₂ and xₜ₊₁",
            "360$^\\circ$ Video": "360° Video",
            "$Q^\\pi$-Realizable MDPs": "Q^π-Realizable MDPs",
            "$O(\\frac{\\sqrt{d}}{K^{1/4}})$ Rate": "O(√d/K^(1/4)) Rate",
            "$\\mathbf{\\mathbb{E}^{FWI}}$: Benchmarks": "E^(FWI): Benchmarks",
            "Layers:\\\\ Exact Mean-Field Analysis": "Layers: Exact Mean-Field Analysis",
            "\\(\\varepsilon\\)-Optimally Solving": "ε-Optimally Solving",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(expected, display_title(raw))

    def test_plain_titles_and_lone_dollar_signs_are_untouched(self) -> None:
        self.assertEqual("Attention Is All You Need", display_title("Attention Is All You Need"))
        self.assertEqual("Training for $5", display_title("Training for $5"))
        self.assertEqual("", display_title(""))


if __name__ == "__main__":
    unittest.main()
