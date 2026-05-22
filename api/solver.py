from ortools.sat.python import cp_model
import math

def solve_schedule(request_data: dict):
    doctors = request_data.get("doctors", [])
    pre_assignments = request_data.get("pre_assignments", [])
    
    num_doctors = len(doctors)
    if num_doctors == 0:
        return {"error": "At least one doctor is required."}

    model = cp_model.CpModel()

    # Variables
    # G[d][p]: Green area, Y[d][p]: Yellow area
    G = {}
    Y = {}
    for d in range(num_doctors):
        for p in range(60):
            G[d, p] = model.NewBoolVar(f"G_{d}_{p}")
            Y[d, p] = model.NewBoolVar(f"Y_{d}_{p}")

    # 1. Coverage constraints
    # Green P1 (0..39): 1 doctor
    for p in range(40):
        model.AddExactlyOne([G[d, p] for d in range(num_doctors)])
    
    # Green P2 (40..59): 2 doctors
    for p in range(40, 60):
        model.Add(sum(G[d, p] for d in range(num_doctors)) == 2)
    
    # Yellow (0..59): 1 doctor
    for p in range(60):
        model.AddExactlyOne([Y[d, p] for d in range(num_doctors)])

    # 2. Cannot be in both areas at the same time
    for d in range(num_doctors):
        for p in range(60):
            model.Add(G[d, p] + Y[d, p] <= 1)

    # 3. Green Area continuous length constraints (min 4, max 12)
    min_len = 4
    max_len = 12
    for d in range(num_doctors):
        w = [G[d, p] for p in range(60)]
        
        # Max length: forbid 13 consecutive ones
        for p in range(60 - max_len):
            model.AddBoolOr([w[p+i].Not() for i in range(max_len + 1)])
            
        # Min length: forbid runs of length 1, 2, ..., min_len-1
        for length in range(1, min_len):
            # In the middle
            for p in range(1, 60 - length):
                # 0 followed by `length` ones followed by 0
                forbidden = [w[p-1]] + [w[p+i].Not() for i in range(length)] + [w[p+length]]
                model.AddBoolOr(forbidden)
            
            # At the start
            forbidden_start = [w[i].Not() for i in range(length)] + [w[length]]
            model.AddBoolOr(forbidden_start)
            
            # At the end
            forbidden_end = [w[59 - length]] + [w[59 - i].Not() for i in range(length)]
            model.AddBoolOr(forbidden_end)

    # 4. Pre-assignments
    # Example: {"doctor_index": 0, "area": "green", "period": 0}
    for pa in pre_assignments:
        d = pa["doctor_index"]
        p = pa["period"]
        if pa["area"] == "green":
            model.Add(G[d, p] == 1)
        elif pa["area"] == "yellow":
            model.Add(Y[d, p] == 1)

    # 4.5. Yellow Area Contiguous Block Constraint
    # Enforce that the yellow shifts for each doctor are a single continuous block.
    for d in range(num_doctors):
        starts = [Y[d, 0]]
        for p in range(1, 60):
            start_var = model.NewBoolVar(f"Y_start_{d}_{p}")
            # start_var >= Y[d, p] - Y[d, p-1]
            model.Add(start_var - Y[d, p] + Y[d, p-1] >= 0)
            starts.append(start_var)
        model.Add(sum(starts) <= 1)

    # 5. Workload Balance
    total_green_1 = {}
    total_green_2 = {}
    total_yellow = {}
    total_work = {}
    
    for d in range(num_doctors):
        total_green_1[d] = sum(G[d, p] for p in range(40))
        total_green_2[d] = sum(G[d, p] for p in range(40, 60))
        total_yellow[d] = sum(Y[d, p] for p in range(60))
        total_work[d] = total_green_1[d] + total_green_2[d] + total_yellow[d]

    # Handle Exemptions
    exempt_docs = []
    regular_docs = []
    
    for d, doc in enumerate(doctors):
        if doc.get("is_exempt", False) and "target_total_minutes" in doc:
            # 1 period = 15 mins
            target_periods = doc["target_total_minutes"] // 15
            model.Add(total_work[d] == target_periods)
            exempt_docs.append(d)
        else:
            regular_docs.append(d)

    # Balance regular doctors
    # To balance, we minimize the difference between the max and min values for each category
    if len(regular_docs) > 0:
        max_total = model.NewIntVar(0, 140, "max_total")
        min_total = model.NewIntVar(0, 140, "min_total")
        for d in regular_docs:
            model.Add(total_work[d] <= max_total)
            model.Add(total_work[d] >= min_total)
            
        max_g1 = model.NewIntVar(0, 40, "max_g1")
        min_g1 = model.NewIntVar(0, 40, "min_g1")
        for d in regular_docs:
            model.Add(total_green_1[d] <= max_g1)
            model.Add(total_green_1[d] >= min_g1)

        max_g2 = model.NewIntVar(0, 40, "max_g2")
        min_g2 = model.NewIntVar(0, 40, "min_g2")
        for d in regular_docs:
            model.Add(total_green_2[d] <= max_g2)
            model.Add(total_green_2[d] >= min_g2)
            
        max_y = model.NewIntVar(0, 60, "max_y")
        min_y = model.NewIntVar(0, 60, "min_y")
        for d in regular_docs:
            model.Add(total_yellow[d] <= max_y)
            model.Add(total_yellow[d] >= min_y)

        # Objective: minimize differences
        # We give highest priority to total work balance, then parts
        model.Minimize(
            (max_total - min_total) * 1000 + 
            (max_g1 - min_g1) * 100 + 
            (max_g2 - min_g2) * 100 + 
            (max_y - min_y) * 100
        )

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        schedule = []
        for p in range(60):
            period_data = {
                "period": p,
                "time": f"{9 + p // 4:02d}:{(p % 4) * 15:02d}",
                "green": [],
                "yellow": []
            }
            for d in range(num_doctors):
                if solver.Value(G[d, p]):
                    period_data["green"].append(doctors[d]["id"])
                if solver.Value(Y[d, p]):
                    period_data["yellow"].append(doctors[d]["id"])
            schedule.append(period_data)
            
        # Also return stats
        stats = {}
        for d in range(num_doctors):
            stats[doctors[d]["id"]] = {
                "total_green_1": solver.Value(total_green_1[d]) * 15,
                "total_green_2": solver.Value(total_green_2[d]) * 15,
                "total_yellow": solver.Value(total_yellow[d]) * 15,
                "total_minutes": solver.Value(total_work[d]) * 15
            }
            
        return {
            "status": "success",
            "schedule": schedule,
            "stats": stats
        }
    else:
        return {"status": "error", "message": "No feasible solution found."}

if __name__ == "__main__":
    # Test
    test_data = {
        "doctors": [
            {"id": "doc1", "name": "Dr. Ali"},
            {"id": "doc2", "name": "Dr. Ayşe"},
            {"id": "doc3", "name": "Dr. Fatma"},
            {"id": "doc4", "name": "Dr. Mehmet"},
            {"id": "doc5", "name": "Dr. Veli"}
        ],
        "pre_assignments": [
            {"doctor_index": 0, "area": "green", "period": 0}
        ]
    }
    result = solve_schedule(test_data)
    print(result["status"])
    if result["status"] == "success":
        for k, v in result["stats"].items():
            print(f"{k}: {v}")
