# constants
N_PEERS=300
SEED_MIN=0
SEED_MAX=19

# initialization
sudo rm -rf ./results

run_simulation_one_seed() {
    SEED=$1

    echo "Running scale: N_PEERS $N_PEERS seed $i"

    sudo mn -c > /dev/null 2>&1
    ulimit -n 65535 > /dev/null 2>&1
    ulimit -u 65535 > /dev/null 2>&1
    sudo sysctl -w fs.file-max=2097152 > /dev/null 2>&1
    sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535" > /dev/null 2>&1

    sudo rm -rf ./tmp
    mkdir -p ./tmp/contact
    mkdir -p ./tmp/scenario

    sudo rm -rf ./results/$N_PEERS/$SEED
    mkdir -p ./results/$N_PEERS/$SEED
    
    sudo python3 setup_scale.py --n_peers $N_PEERS --seed $SEED > /dev/null 2>&1
}

run_simulation_all() {
    for i in $(seq $SEED_MIN $SEED_MAX); do
        run_simulation_one_seed $i
    done
}

run_pkg() {
    PKG=$1

    cd abyss_test
    ./pkg_load.sh ${PKG}
    cd ..
    
    sudo rm -rf ./results
    run_simulation_all
    mkdir -p scale/${PKG}/
    cp results/${N_PEERS}/ -r scale/${PKG}/
}

run_simulation_one_seed_cs() {
    SEED=$1

    echo "Running scale: N_PEERS $N_PEERS seed $i"

    sudo mn -c > /dev/null 2>&1
    ulimit -n 65535 > /dev/null 2>&1
    ulimit -u 65535 > /dev/null 2>&1
    sudo sysctl -w fs.file-max=2097152 > /dev/null 2>&1
    sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535" > /dev/null 2>&1

    sudo rm -rf ./tmp
    mkdir -p ./tmp/contact
    mkdir -p ./tmp/scenario

    sudo rm -rf ./results/$N_PEERS/$SEED
    mkdir -p ./results/$N_PEERS/$SEED
    
    sudo python3 setup_scale_cs.py --n_peers $N_PEERS --seed $SEED > /dev/null 2>&1
}

run_simulation_all_cs() {
    for i in $(seq $SEED_MIN $SEED_MAX); do
        run_simulation_one_seed_cs $i
    done
}

run_cs() {
    cd abyss_test
    ./pkg_load.sh dev-eval-naive
    cd ..
    
    sudo rm -rf ./results
    run_simulation_all_cs
    mkdir -p scale/client-server/
    cp results/${N_PEERS}/ -r scale/client-server/
}

run_pkg dev-v2
run_pkg dev-eval-naive
run_pkg dev-eval-trickle
run_cs