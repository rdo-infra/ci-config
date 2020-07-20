promoter
========

This role is meant to run in 3 different environments:

   STANDALONE, ZUUL, and MOLECULE

 - STANDALONE (production promoter server in real host or vm)
   should be run only after merging tested code, to actually provision the real server
   with continuous deployment afterwards. RUNS THE ROLE AS ROOT

 - ZUUL ci job in staging promoter (nodepool node)
   watch the test in your ci job

 - MOLECULE testing (local docker driver)
   test and iterate over it before submitting changes
   This environment should be taken into consideration, but major
   task for it should be added in the molecule playbooks directly
   and not here

   ALL refers to all environments above
