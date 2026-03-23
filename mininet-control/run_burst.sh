# constants
N_PEERS=130
N_CHURN=30
SEED_MIN=0
SEED_MAX=9

run_simulation_one_seed() {
    SEED=$1

    echo "Running burst: N_PEERS $N_PEERS N_CHURN $N_CHURN seed $i"

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
    
    sudo python3 setup_burst.py --n_peers $N_PEERS --n_churn $N_CHURN --seed $SEED
}

run_simulation_all() {
    for i in $(seq $SEED_MIN $SEED_MAX); do
        run_simulation_one_seed $i
    done
}

run_ablation() {
    TARGET=$1
    MIN_INTERVAL=$2
    UNIT_INTERVAL=$3

    cd abyss_test
    ./pkg_load.sh $TARGET
    cd ..
    
    cd abyss_test
    sed -i "s/\(TimerMinInterval  = \)400/\1${MIN_INTERVAL}/" ./abyss_core/and/utils.go
    sed -i "s/\(TimerUnitInterval = \)300/\1${UNIT_INTERVAL}/" ./abyss_core/and/utils.go
    go build -o scenario_run .
    cd ..

    sudo rm -rf ./results
    run_simulation_all
    #rm -rf ablation/${TARGET}/t_min_${MIN_INTERVAL}_unit_${UNIT_INTERVAL}/${N_PEERS}/
    mkdir -p ablation/${TARGET}/t_min_${MIN_INTERVAL}_unit_${UNIT_INTERVAL}/
    cp results/${N_PEERS}/ -r ablation/${TARGET}/t_min_${MIN_INTERVAL}_unit_${UNIT_INTERVAL}/
}

run_pkg() {
    PKG=$1

    cd abyss_test
    ./pkg_load.sh ${PKG}
    cd ..
    
    sudo rm -rf ./results
    run_simulation_all
    rm -rf burst/${PKG}/${N_PEERS}/
    mkdir -p burst/${PKG}/
    cp results/${N_PEERS}/ -r burst/${PKG}/
}

run_simulation_one_seed_cs() {
    SEED=$1

    echo "Running burst: N_PEERS $N_PEERS N_CHURN $N_CHURN seed $i"

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
    rm -rf burst/client-server/${N_PEERS}/
    mkdir -p burst/client-server/
    cp results/${N_PEERS}/ -r burst/client-server/
}

# run_ablation dev-v2 0 300
# run_ablation dev-v2 200 300
# run_ablation dev-v2 400 300
# run_ablation dev-v2 600 300

# run_ablation dev-v2 300 100
# run_ablation dev-v2 300 300
# run_ablation dev-v2 300 500
# run_ablation dev-v2 300 700

N_PEERS=130
N_CHURN=30
run_pkg dev-v2
# run_pkg dev-eval-trickle
# run_cs

# N_PEERS=160
# N_CHURN=60
# run_pkg dev-v2
# run_pkg dev-eval-trickle
# run_cs

# N_PEERS=190
# N_CHURN=90
# run_pkg dev-v2
# run_pkg dev-eval-trickle
# run_cs