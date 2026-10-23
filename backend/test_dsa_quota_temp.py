from tools import dsa_seed_runner as r

source = """def f():
    open('x', 'w').write('a' * (2 * 1024 * 1024))
    return 1
"""

print(r.run_calls(source, "f", [[]]))
