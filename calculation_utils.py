from collections import defaultdict

def calculate_summary(expenses, persons):
    totals = defaultdict(float)
    for e in expenses:
        totals[e.person] += e.amount

    grand_total = sum(totals.values())
    average = grand_total / len(persons)

    differences = {p: round(totals[p] - average, 2) for p in persons}

    settlement = []
    owes = [(p, -diff) for p, diff in differences.items() if diff < 0]
    gets = [(p, diff) for p, diff in differences.items() if diff > 0]
    owes.sort(key=lambda x: x[1])
    gets.sort(key=lambda x: x[1], reverse=True)

    i, j = 0, 0
    while i < len(owes) and j < len(gets):
        owe_p, owe_amt = owes[i]
        get_p, get_amt = gets[j]
        amount = min(owe_amt, get_amt)
        settlement.append(f"{owe_p} pays ₹{amount:.2f} to {get_p}")
        owes[i] = (owe_p, owe_amt - amount)
        gets[j] = (get_p, get_amt - amount)
        if owes[i][1] == 0: i += 1
        if gets[j][1] == 0: j += 1

    return totals, grand_total, average, differences, settlement
