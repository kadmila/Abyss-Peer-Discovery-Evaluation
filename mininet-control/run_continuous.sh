# constants
N_PEERS=200
N_CHURN=10
SEED_MIN=0
SEED_MAX=4

run_simulation_one_seed() {
    SEED=$1

    echo "Running continuous churn: N_PEERS $N_PEERS N_CHURN $N_CHURN seed $i"

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
    
    sudo python3 setup_burst.py --n_peers $N_PEERS --n_churn $N_CHURN --seed $SEED > /dev/null 2>&1
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
    rm -rf continuous/${PKG}/${N_PEERS}/
    mkdir -p continuous/${PKG}/
    cp results/${N_PEERS}/ -r continuous/${PKG}/
}

run_simulation_one_seed_cs() {
    SEED=$1

    echo "Running continuous churn: N_PEERS $N_PEERS N_CHURN $N_CHURN seed $i"

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
    
    sudo python3 setup_burst_cs.py --n_peers $N_PEERS --n_churn $N_CHURN --seed $SEED > /dev/null 2>&1
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
    rm -rf continuous/client-server/${N_PEERS}/
    mkdir -p continuous/client-server/
    cp results/${N_PEERS}/ -r continuous/client-server/
}

N_PEERS=200
N_CHURN=10
run_pkg dev-v2
run_pkg dev-eval-trickle
run_cs

N_PEERS=130
N_CHURN=3
run_pkg dev-v2
run_pkg dev-eval-trickle
run_cs

N_PEERS=110
N_CHURN=1
run_pkg dev-v2
run_pkg dev-eval-trickle
run_cs