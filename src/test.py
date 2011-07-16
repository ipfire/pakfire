
import _pakfire
print dir(_pakfire)

pool = _pakfire.Pool("i686")
print pool

repo1 = _pakfire.Repo(pool, "test")
repo2 = _pakfire.Repo(pool, "installed")
print repo1, repo2

pool.set_installed(repo2)

solv1 = _pakfire.Solvable(repo1, "a", "1.0-2", "i686")
print solv1, solv1.get_name(), solv1.get_evr(), solv1.get_arch()
print dir(solv1)

solv2 = _pakfire.Solvable(repo2, "b", "2.0-2", "i686")
print solv2, solv2.get_name(), solv2.get_evr(), solv2.get_arch()

solv3 = _pakfire.Solvable(repo1, "b", "2.0-3", "i686")
print solv3, solv3.get_name(), solv3.get_evr(), solv3.get_arch()

relation1 = _pakfire.Relation(pool, "b", "2.0-3", _pakfire.REL_GE)
print relation1

relation2 = _pakfire.Relation(pool, "/bin/laden")
print relation2

solv1.add_requires(relation1)
solv1.add_provides(relation2)

relation3 = _pakfire.Relation(pool, "a")
print relation3

#solv2.add_conflicts(relation3)
#solv3.add_conflicts(relation3)

pool.prepare()

solver = _pakfire.Solver(pool)
print solver

solver.set_allow_uninstall(True)
print "allow_uninstall", solver.get_allow_uninstall()
print "allow_downgrade", solver.get_allow_downgrade()


request = _pakfire.Request(pool)
print request

request.install_solvable(solv1)
#request.install_solvable_name("a")

res = solver.solve(request)
print "Result:", res

if res:
	transaction = _pakfire.Transaction(solver)
	print transaction, transaction.steps()

	for step in transaction.steps():
		print "Step %s:" % step
		solvable = step.get_solvable()
		print "  solv: %s" % solvable, solvable.get_name(), solvable.get_evr()
		print "  type: %s" % step.get_type()
		print

print pool.providers("b")

print "Pool size: %d" % pool.size()
