"""Keep duplicated public price tables aligned with recorded live challenges.

Refresh the public, credential-free fixture when verifying new API prices.
These are payment challenges, not proof of execution or metering units.
"""
import json
from decimal import Decimal
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads((ROOT / 'tests/fixtures/pricing-live.json').read_text())
NAMES = {
    '/v1/ai/tts': 'Text-to-Speech',
    '/v1/agents/resources/images/generate': 'Image Generation',
    '/v1/agents/resources/embeddings': 'Embeddings',
    '/v1/agents/resources/vision/analyze': 'Vision',
    '/v1/comms/email/send': 'Email',
    '/v1/agents/resources/search': 'Web Search',
}


class PricingTests(unittest.TestCase):
    def test_tables_match_live_challenges(self):
        for filename in ['README.md', 'docs/pricing.md', 'docs/api-reference.md']:
            doc = (ROOT / filename).read_text()
            for response in SNAPSHOT['responses']:
                endpoint = response['endpoint']
                if endpoint not in NAMES:
                    continue
                usd = Decimal(str(response['credits_cost']))
                self.assertEqual(usd * 1000000, Decimal(response['usdc_amount']))
                label = f'`{endpoint}`' if filename.endswith('api-reference.md') else NAMES[endpoint]
                rows = [line for line in doc.splitlines() if line.startswith('| ') and f'| {label} |' in line]
                self.assertTrue(rows, (filename, label))
                for row in rows:
                    self.assertIn(f'{(usd * 1000).normalize():f} ₭', row)
                    if filename != 'docs/api-reference.md':
                        self.assertIn(f'${usd:g}', row)
            self.assertIn('Last verified: ' + SNAPSHOT['last_verified'], doc)
