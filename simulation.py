import json
from dataclasses import dataclass
from pathlib import Path

SOL_MINT = "So11111111111111111111111111111111111111112"
TOKEN_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


@dataclass
class PoolState:
    token_reserve: float
    sol_reserve: float

    def price(self) -> float:
        return self.sol_reserve / self.token_reserve

    def cp(self) -> float:
        return self.token_reserve * self.sol_reserve

    def swap_sol_for_token(self, sol_in: float) -> float:
        new_sol_reserve = self.sol_reserve + sol_in
        new_token_reserve = self.cp() / new_sol_reserve
        token_out = self.token_reserve - new_token_reserve
        self.sol_reserve = new_sol_reserve
        self.token_reserve = new_token_reserve
        return token_out

    def swap_token_for_sol(self, token_in: float) -> float:
        new_token_reserve = self.token_reserve + token_in
        new_sol_reserve = self.cp() / new_token_reserve
        sol_out = self.sol_reserve - new_sol_reserve
        self.token_reserve = new_token_reserve
        self.sol_reserve = new_sol_reserve
        return sol_out


def create_tx(
    signature: str,
    slot: int,
    signer: str,
    token_in: str,
    token_out: str,
    amount_in: float,
    amount_out: float,
    program="Raydium CLMM",
):
    return {
        "signature": signature,
        "slot": slot,
        "tx_index": 1,
        "signer": signer,
        "swap_program": program,
        "pool_name": "SIMULATED_POOL",
        "token_in": token_in,
        "token_out": token_out,
        "amount_in": amount_in,
        "amount_out": amount_out,
        "priority_fee": 0,
        "tip_account": None,
        "tip_amount": 0,
    }


def run_simulation(
    pool: PoolState,
    bot_sol_spend: float,
    victim_sol_spend: float,
    slot_gap_front_to_victim=1,
    slot_gap_victim_to_back=3,
):

    initial_price = pool.price()
    token_acquired = pool.swap_sol_for_token(bot_sol_spend)
    victim_token_out = pool.swap_sol_for_token(victim_sol_spend)

    sol_returned = pool.swap_token_for_sol(token_acquired)

    frontrun_tx = create_tx(
        "SIM_FRONT",
        10_000,
        "BOT_WALLET_ABC",
        SOL_MINT,
        TOKEN_MINT,
        bot_sol_spend,
        token_acquired,
    )

    victim_tx = create_tx(
        "SIM_VICTIM",
        10_000 + slot_gap_front_to_victim,
        "VICTIM_WALLET_XYZ",
        SOL_MINT,
        TOKEN_MINT,
        victim_sol_spend,
        victim_token_out,
    )

    backrun_tx = create_tx(
        "SIM_BACK",
        10_000 + slot_gap_front_to_victim + slot_gap_victim_to_back,
        "BOT_WALLET_ABC",
        TOKEN_MINT,
        SOL_MINT,
        token_acquired,
        sol_returned,
    )

    result = {
        "initial_price": initial_price,
        "transactions": [frontrun_tx, victim_tx, backrun_tx],
        "bot_profit_sol": sol_returned - bot_sol_spend,
        "victim_loss_tokens": (victim_sol_spend / initial_price) - victim_token_out,
        "final_price": pool.price(),
    }

    return result


def print_simulation_summary(result: dict, pool: PoolState) -> None:
    print("\n" + "=" * 70)
    print("WIDE SANDWICH ATTACK SIMULATION")
    print("=" * 70)

    print("\n POOL STATE")
    print("-" * 70)
    print(f"  Initial Token Reserve: {pool.token_reserve:,.0f}")
    print(f"  Initial SOL Reserve:   {pool.sol_reserve:,.2f} SOL")
    print(f"  Initial Price:         {result['initial_price']:.8f} SOL/token")
    print(f"  Final Price:           {result['final_price']:.8f} SOL/token")
    print(
        f"  Price Change:          {((result['final_price'] / result['initial_price']) - 1) * 100:+.2f}%"
    )

    print("\n BOT STRATEGY")
    print("-" * 70)
    front_tx = result["transactions"][0]
    back_tx = result["transactions"][2]
    print(f"  Front-run (Slot {front_tx['slot']}):")
    print(f"    Spent:    {front_tx['amount_in']:.6f} SOL")
    print(f"    Received: {front_tx['amount_out']:.6f} tokens")
    print(f"  Back-run (Slot {back_tx['slot']}):")
    print(f"    Spent:    {back_tx['amount_in']:.6f} tokens")
    print(f"    Received: {back_tx['amount_out']:.6f} SOL")
    print(f"    Net Profit: {result['bot_profit_sol']:.6f} SOL")
    print(
        f"     ROI:       {(result['bot_profit_sol'] / front_tx['amount_in']) * 100:.2f}%"
    )

    print("\n VICTIM IMPACT")
    print("-" * 70)
    victim_tx = result["transactions"][1]
    expected_tokens = victim_tx["amount_in"] / result["initial_price"]
    print(f"  Victim Swap (Slot {victim_tx['slot']}):")
    print(f"    Spent:         {victim_tx['amount_in']:.6f} SOL")
    print(f"    Expected:      {expected_tokens:.6f} tokens (at initial price)")
    print(f"    Actually Got:  {victim_tx['amount_out']:.6f} tokens")
    print(f"   Loss: {result['victim_loss_tokens']:.6f} tokens")
    print(f"     Loss %: {(result['victim_loss_tokens'] / expected_tokens) * 100:.2f}%")

    print("\nTIMING")
    print("-" * 70)
    slots = [tx["slot"] for tx in result["transactions"]]
    print(f"  Front-run → Victim:   {slots[1] - slots[0]} slot(s)")
    print(f"  Victim → Back-run:     {slots[2] - slots[1]} slot(s)")
    print(f"  Total Span:            {slots[2] - slots[0]} slot(s)")

    print("\n" + "=" * 70)


def save_simulation():
    print("\n" + "=" * 70)
    print("GENERATING WIDE SANDWICH SIMULATION")
    print("=" * 70)

    pool = PoolState(token_reserve=1_000_000, sol_reserve=500)
    print(
        f"\nInitializing pool: {pool.token_reserve:,.0f} tokens / {pool.sol_reserve:.2f} SOL"
    )

    result = run_simulation(
        pool,
        bot_sol_spend=20,
        victim_sol_spend=30,
        slot_gap_front_to_victim=1,
        slot_gap_victim_to_back=3,
    )

    print_simulation_summary(result, pool)

    output_path = RESULTS_DIR / "simulation.json"
    with open(output_path, "w") as f:
        json.dump({"transactions": result["transactions"]}, f, indent=2)

    print(f"simulation.json saved to {output_path}\n")


if __name__ == "__main__":
    save_simulation()
