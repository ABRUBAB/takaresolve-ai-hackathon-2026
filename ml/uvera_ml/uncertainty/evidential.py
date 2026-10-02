"""Evidential classification head (Sensoy et al., 2018): a small MLP that outputs Dirichlet evidence.

Uncertainty u = K / sum(alpha) is an explicit "I don't know" mass. We compare it honestly against a calibrated
logistic regression; if it is not better, the report says so and the product uses the simpler model.
"""
from __future__ import annotations

import numpy as np


def _torch():
    import torch
    import torch.nn as nn

    return torch, nn


class EvidentialHead:
    def __init__(self, n_classes: int, hidden: int = 256, epochs: int = 40, lr: float = 1e-3, seed: int = 42,
                 anneal_epochs: int = 10, device: str | None = None):
        self.K, self.hidden, self.epochs, self.lr, self.seed, self.anneal = n_classes, hidden, epochs, lr, seed, anneal_epochs
        self.device = device

    def _build(self, d_in):
        torch, nn = _torch()
        torch.manual_seed(self.seed)
        self.net = nn.Sequential(nn.Linear(d_in, self.hidden), nn.ReLU(), nn.Dropout(0.2), nn.Linear(self.hidden, self.K))
        self.device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.net.to(self.device)

    def _loss(self, alpha, y_onehot, epoch):
        torch, _ = _torch()
        S = alpha.sum(dim=1, keepdim=True)
        p = alpha / S
        mse = ((y_onehot - p) ** 2).sum(1) + (p * (1 - p) / (S + 1)).sum(1)
        alpha_t = y_onehot + (1 - y_onehot) * alpha  # remove evidence of the true class before the KL term
        S_t = alpha_t.sum(dim=1, keepdim=True)
        kl = (torch.lgamma(S_t).squeeze(1) - torch.lgamma(torch.tensor(float(self.K), device=alpha.device))
              - torch.lgamma(alpha_t).sum(1)
              + ((alpha_t - 1) * (torch.digamma(alpha_t) - torch.digamma(S_t))).sum(1))
        lam = min(1.0, epoch / max(1, self.anneal))
        return (mse + lam * kl).mean()

    def fit(self, X: np.ndarray, y: np.ndarray, batch_size: int | None = None) -> "EvidentialHead":
        torch, nn = _torch()
        batch_size = batch_size or int(min(256, max(32, len(X) // 30)))  # enough steps on small data
        self._build(X.shape[1])
        Xt = torch.tensor(X, dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.long)
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr, weight_decay=1e-4)
        g = torch.Generator().manual_seed(self.seed)
        for epoch in range(self.epochs):
            self.net.train()
            perm = torch.randperm(len(Xt), generator=g)
            for i in range(0, len(Xt), batch_size):
                idx = perm[i:i + batch_size]
                xb, yb = Xt[idx].to(self.device), yt[idx].to(self.device)
                alpha = nn.functional.softplus(self.net(xb)) + 1
                loss = self._loss(alpha, nn.functional.one_hot(yb, self.K).float(), epoch)
                opt.zero_grad()
                loss.backward()
                opt.step()
        return self

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Returns (class probabilities, uncertainty u in (0, 1])."""
        torch, nn = _torch()
        self.net.eval()
        with torch.no_grad():
            out = []
            for i in range(0, len(X), 2048):
                xb = torch.tensor(X[i:i + 2048], dtype=torch.float32, device=self.device)
                out.append((nn.functional.softplus(self.net(xb)) + 1).cpu().numpy())
        alpha = np.vstack(out)
        S = alpha.sum(1, keepdims=True)
        return alpha / S, (self.K / S).ravel()

    def save(self, path: str) -> None:
        torch, _ = _torch()
        torch.save({"state_dict": self.net.state_dict(), "K": self.K, "hidden": self.hidden,
                    "d_in": self.net[0].in_features}, path)
