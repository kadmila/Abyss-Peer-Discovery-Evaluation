package main

import (
	"crypto/ed25519"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path"
	"time"

	"github.com/kadmila/Abyss-Browser/abyss_core/ahost"
	"golang.org/x/crypto/ssh"
)

func main() {
	// Parse CLI arguments
	var id string
	var contact_dir string
	var time_start_ms int64
	var duration int64
	var scenario_path string
	var output_path string
	flag.StringVar(&id, "id", "", "host id")
	flag.StringVar(&contact_dir, "contact_dir", "", "path to directory for sharing contact information")
	flag.Int64Var(&time_start_ms, "t_start", 0, "time to start the scenario")
	flag.Int64Var(&duration, "duration", 0, "maximum execution duration")
	flag.StringVar(&scenario_path, "scenario", "", "path to scenario JSON file")
	flag.StringVar(&output_path, "out", "", "path to output file")
	flag.Parse()

	// Parse scenario file if provided
	var scenario []map[string]string
	if scenario_path != "" {
		scenarioData, err := os.ReadFile(scenario_path)
		if err != nil {
			log.Fatalf("Error reading scenario file: %v", err)
		}
		err = json.Unmarshal(scenarioData, &scenario)
		if err != nil {
			log.Fatalf("Error parsing scenario JSON: %v", err)
		}
		log.Printf("Loaded scenario with %d entries", len(scenario))
	}

	// Read ../credentials/{id}.pem and parse key
	key_pem, err := os.ReadFile(fmt.Sprintf("./credentials/%s.pem", id))
	if err != nil {
		log.Fatalf("Error reading private key file: %v", err)
	}
	private_key, err := ssh.ParseRawPrivateKey(key_pem)
	if err != nil {
		log.Fatalf("Error parsing private key: %v", err)
	}

	ed25519_priv_key, ok := private_key.(*ed25519.PrivateKey) //wtf?
	if !ok {
		log.Fatalf("Unsupported key type, expected ed25519 private key")
	}

	// Construct Abyss host
	host, err := ahost.NewAbyssHost(*ed25519_priv_key)
	if err != nil {
		log.Fatalf("Error constructing Abyss host: %v", err)
	}

	err = host.Bind()
	if err != nil {
		log.Fatalf("Error binding Abyss host: %v", err)
	}

	go host.Serve()

	// Write contact information
	rc_f, err := os.OpenFile(path.Join(contact_dir, id+"_rc"), os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
	}
	if _, err := rc_f.WriteString(host.RootCertificate()); err != nil {
		log.Fatal(err)
	}
	rc_f.Close() // Ensure the file is closed
	hs_f, err := os.OpenFile(path.Join(contact_dir, id+"_hs"), os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
	}
	if _, err := hs_f.WriteString(host.HandshakeKeyCertificate()); err != nil {
		log.Fatal(err)
	}
	hs_f.Close() // Ensure the file is closed
	id_f, err := os.OpenFile(path.Join(contact_dir, id+"_id"), os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
	}
	if _, err := id_f.WriteString(host.ID()); err != nil {
		log.Fatal(err)
	}
	id_f.Close() // Ensure the file is closed

	scenario_runner := NewScenarioRunner(contact_dir, time.UnixMilli(time_start_ms), time.Duration(duration)*time.Second, scenario, host, output_path)
	scenario_runner.Run()
}
