"""Explicit opt-in evaluation budget; conservative reservations, never billing claims."""

import math
from pathlib import Path
from .provider import ProviderError
from .storage import canonical


class SpendingLimit(ProviderError):
    pass


class SpendingBudget:
    def __init__(self, usd, input_per_million, output_per_million, path):
        if any(
            type(v) not in (int, float) or not math.isfinite(v) or v <= 0
            for v in (usd, input_per_million, output_per_million)
        ):
            raise ValueError(
                "Explicit positive spending budget and model prices required"
            )
        self.limit = usd
        self.input_price = input_per_million
        self.output_price = output_per_million
        self.path = Path(path)
        if self.path.exists():
            raise ValueError(
                "Budget ledger exists; choose a fresh evaluation directory"
            )
        self.reservations = []
        self.spent = 0.0
        self._save()

    def reserve(self, payload):
        # UTF-8 bytes plus a deliberately large framing allowance. This is a
        # conservative local estimate, not a provider billing or tokenizer API.
        input_bound = len(canonical(payload).encode()) + 4096
        output_bound = payload["max_output_tokens"]
        estimate = (
            input_bound * self.input_price + output_bound * self.output_price
        ) / 1_000_000
        if self.spent + estimate > self.limit:
            raise SpendingLimit(
                "Evaluation spending budget reservation exhausted; no request sent"
            )
        self.spent += estimate
        self.reservations.append(
            dict(
                request=len(self.reservations) + 1,
                input_token_bound=input_bound,
                output_token_bound=output_bound,
                reserved_usd=estimate,
            )
        )
        self._save()  # Persist before sending, including attempts with lost responses.

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            canonical(
                dict(
                    authorized_usd=self.limit,
                    reserved_usd=self.spent,
                    input_usd_per_million=self.input_price,
                    output_usd_per_million=self.output_price,
                    reservations=self.reservations,
                    note="No refunds for retries, refusals or missing usage. User-supplied prices and conservative token estimate; not an invoice or provider-side hard spending cap.",
                )
            )
            + "\n"
        )
