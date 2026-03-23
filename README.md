# Abyss-Peer-Discovery-Evaluation
Mininet2 evaluation setup for abyss peer discovery

*** Execution Order ***
1. run ./init.sh
2. (optional) open ./main.ipynb, and run all code snippets. This will take a while. 
If you want to use the same data with us, you don't need to run this.
This script updates ./network_stats.json
Unfortunately, this script may fail if you are unlucky - if a RIPE anchor terminates while you are downloading.
There are not many options; just run it again. You may want to decrease the query time interval (currently, it's an hour).

3. (optional) open ./config_gen.ipynb, and run all code snippets.
This scripts updates ./mininiet-control/city_config.json

4. In ./mininet-control directory, run ./run_all.sh

5. In ./mininet-control/plotter directory, _ifstats.ipynb and _reachability.ipynb should be executed first.