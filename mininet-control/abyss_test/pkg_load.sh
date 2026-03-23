rm -rf ./abyss_core
mkdir abyss_core
cp -r $1/* ./abyss_core/
go build -o scenario_run .
