"""
Athena LLM Prompt Templates
The LLM acts as a senior credit analyst adjusting the quantitative base score
by -50 to +50 points based on qualitative signals in text data.
"""
from __future__ import annotations

import json


SYSTEM_CONTEXT = """
You are a senior credit risk analyst at Athena Credit Initiative in Africa.
Your role is to apply qualitative judgment to a quantitative credit score.

You will receive:
1. A quantitative base score and CRB contribution already computed.
2. A summary of the customer's transaction history (categories, patterns).
3. CRB extracted metrics (bureau score, NPA count, default history).

You must output a JSON object with exactly two keys:
- "adjustment": an integer between -50 and +50 (inclusive). 
  Positive = improvement to score, Negative = deduction.
- "reasoning": a list of 3-6 bullet strings (each max 20 words) explaining 
  your adjustments. Be specific about which signals drove the decision.

SCORING GUIDELINES:
Positive signals (+):
  - Regular salary deposits (employment stability)  +5 to +15
  - Consistent monthly savings pattern      +5 to +10
  - Utility bill payments (responsible behaviour)    +3 to +8
  - Educational / medical spending          +3 to +5
  - Zero or declining trend in late payments         +5 to +15
  - Improving trend in CRB score over time  +5 to +10

Negative signals (-):
  - Betting / gambling transactions > 3% of income   -5 to -15
  - Cash cycling (repeated withdrawal of full balance) -5 to -10
  - High SMS/data spend with no productive outflows   -3 to -7
  - Active NPAs or recent defaults          -10 to -30
  - Irregular income with high volatility   -5 to -15
  - Rapid increase in CRB enquiries         -3 to -10

IMPORTANT: Base your adjustment ONLY on the data provided. Do not hallucinate.
Output valid JSON only, no markdown fences.
"""


def build_scoring_prompt(
    customer_name: str,
    base_score: float,
    crb_contribution: float,
    transaction_summary: dict,
    crb_metrics: dict,
) -> str:
    """Build the user message for the LLM scoring call."""

    tx = transaction_summary
    crb = crb_metrics

    prompt = f"""
{SYSTEM_CONTEXT}

--- CUSTOMER DATA ---
Customer: {customer_name}
Quantitative Base Score (300-700): {base_score}
CRB Contribution (0-150): {crb_contribution}

--- TRANSACTION SUMMARY (last 6 months) ---
Average Monthly Income: {tx.get('avg_monthly_income', 'N/A')} {tx.get('currency', 'KES')}
Income Coefficient of Variation (stability, lower=better): {tx.get('income_cv', 'N/A')}
Average Monthly Savings: {tx.get('avg_monthly_savings', 'N/A')} {tx.get('currency', 'KES')}
Low Balance Events (<10% of avg income): {tx.get('low_balance_events', 0)}
Spending Categories (% of debit spend):
{json.dumps(tx.get('category_breakdown', {}), indent=2)}
Notable Patterns: {tx.get('patterns', 'None identified')}

--- CRB DATA ({crb.get('crb_name', 'Unknown Bureau')}, as of {crb.get('report_date', 'N/A')}) ---
Bureau Score: {crb.get('bureau_score', 'N/A')}
Non-Performing Accounts (NPA): {crb.get('npa_count', 0)} 
  (Outstanding: {crb.get('npa_outstanding', 0)} {tx.get('currency', 'KES')})
Active Defaults: {crb.get('active_defaults', 0)}
Settled Defaults: {crb.get('settled_defaults', 0)}
Credit Enquiries (last 90 days): {crb.get('enquiries_90d', 0)}
Credit Applications (last 12 months): {crb.get('applications_12m', 0)}

--- TASK ---
Provide your qualitative adjustment and reasoning as a JSON object.
"""
    return prompt.strip()
