package main

import (
	"fmt"
	"log"
	"os"
	"path"
	"strconv"
	"sync"
	"time"

	"github.com/kadmila/Abyss-Browser/abyss_core/ahost"
	"github.com/kadmila/Abyss-Browser/abyss_core/and"
)

// ScenarioRunner executes a sequence of actions defined in a scenario
type ScenarioRunner struct {
	contact_dir string
	time_start  time.Time
	time_end    time.Time
	scenario    []map[string]string
	host        *ahost.AbyssHost
	out_f       *os.File

	world_mtx sync.Mutex
	world     *and.World
}

// NewScenarioRunner creates a new ScenarioRunner with the given scenario and host
func NewScenarioRunner(contact_dir string, time_start time.Time, duration time.Duration, scenario []map[string]string, host *ahost.AbyssHost, output_path string) *ScenarioRunner {
	out_f, err := os.Create(output_path)
	if err != nil {
		log.Fatalf("Error reading scenario file: %v", err)
	}
	return &ScenarioRunner{
		contact_dir: contact_dir,
		time_start:  time_start,
		time_end:    time_start.Add(duration),
		scenario:    scenario,
		host:        host,
		out_f:       out_f,
	}
}

// Run executes the scenario by iterating over each step and waiting until the specified timestamp
func (sr *ScenarioRunner) Run() error {
	go sr.HandleEvents()

	log.Printf("Start")

	for i, step := range sr.scenario {
		timeStr, ok := step["time"]
		if !ok {
			log.Printf("Warning: Step %d missing 'time' field, skipping", i)
			continue
		}

		timestamp, err := strconv.ParseInt(timeStr, 10, 64)
		if err != nil {
			log.Printf("Error: Step %d has invalid timestamp '%s': %v", i, timeStr, err)
			continue
		}

		target_timestamp := sr.time_start.Add(time.Duration(timestamp) * time.Second)
		if target_timestamp.After(sr.time_end) {
			break
		}

		now := time.Now()
		if target_timestamp.After(now) {
			waitDuration := target_timestamp.Sub(now)
			time.Sleep(waitDuration)
		}

		done := make(chan bool, 1)
		tst_s := 0
		go func() {
			// Action
			switch step["do"] {
			case "add":

				peer_id := step["id"]
				rc, err := os.ReadFile(path.Join(sr.contact_dir, peer_id+"_rc"))
				if err != nil {
					log.Fatalf("unable to read file: %v", err)
				}
				hs, err := os.ReadFile(path.Join(sr.contact_dir, peer_id+"_hs"))
				if err != nil {
					log.Fatalf("unable to read file: %v", err)
				}
				sr.host.AppendKnownPeer(string(rc), string(hs))

			case "dial":

				peer_id := step["id"]
				id_hash, err := os.ReadFile(path.Join(sr.contact_dir, peer_id+"_id"))
				if err != nil {
					log.Fatalf("unable to read file: %v", err)
				}
				sr.host.Dial(string(id_hash))

			case "join":

				peer_id := step["id"]
				id_hash, err := os.ReadFile(path.Join(sr.contact_dir, peer_id+"_id"))
				if err != nil {
					log.Fatalf("unable to read file: %v", err)
				}

				sr.world_mtx.Lock()
				if sr.world != nil {
					sr.host.CloseWorld(sr.world) // This automatically frees world path
				}
				sr.world = nil
				sr.world_mtx.Unlock()

				for i := range 100 {
					if i == 99 {
						log.Println("Error: Failed to join. This is a failure.")
						break
					}

					sr.world_mtx.Lock()
					sr.world, err = sr.host.JoinWorld(string(id_hash), "/")
					sr.world_mtx.Unlock()

					if err == nil {
						break
					}
					time.Sleep(time.Millisecond * 100)
				}

			case "open":

				sr.world_mtx.Lock()
				if sr.world != nil {
					sr.host.CloseWorld(sr.world) // This automatically frees world path
				}
				sr.world, err = sr.host.OpenWorld("https://www.example.com")
				sr.world_mtx.Unlock()

			case "close":

				tst_s = 1
				sr.world_mtx.Lock()
				if sr.world != nil {
					tst_s = 2
					sr.host.CloseWorld(sr.world) // This automatically frees world path
				}
				sr.world = nil
				sr.world_mtx.Unlock()

			}
			done <- true
		}()
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			//fatal: timeout for scenario execution
			log.Printf("Fatal: Scenario Execution Timeout: ")
			fmt.Println("failed action: " + step["do"] + strconv.Itoa(tst_s))
			os.Exit(1)
		}
	}

	now := time.Now()
	if sr.time_end.After(now) {
		time.Sleep(sr.time_end.Sub(now))
	}

	sr.out_f.Close()
	log.Printf("Finish")
	return nil
}

func (sr *ScenarioRunner) HandleEvents() {
	event_ch := sr.host.GetEventCh()

	for {
		any_event, ok := <-event_ch
		if !ok {
			break
		}

		switch event := any_event.(type) {
		case *and.EANDWorldEnter:
			sr.host.ExposeWorldForJoin(sr.world, "/") // this should not fail.
			fmt.Fprintf(sr.out_f, "%d E %v\n", time.Now().UnixMilli(), event.WSID)

		case *and.EANDSessionReady:
			fmt.Fprintf(sr.out_f, "%d J %v\n", time.Now().UnixMilli(), event.SessionID)

		case *and.EANDSessionClose:
			fmt.Fprintf(sr.out_f, "%d L %v\n", time.Now().UnixMilli(), event.SessionID)

		case *and.EANDObjectAppend:
		case *and.EANDObjectDelete:
		case *and.EANDWorldLeave:
			fmt.Fprintf(sr.out_f, "%d X %v\n", time.Now().UnixMilli(), event.WSID)
			// case *ahost.EPeerConnected:
			// 	fmt.Fprintf(sr.out_f, "%d Cn %v\n", time.Now().UnixMilli(), event.PeerID)
			// case *ahost.EPeerDisconnected:
			// 	fmt.Fprintf(sr.out_f, "%d Dc %v\n", time.Now().UnixMilli(), event.PeerID)
			// case *ahost.EPeerFound:
			// 	fmt.Fprintf(sr.out_f, "%d Fd %v\n", time.Now().UnixMilli(), event.PeerID)
			// case *ahost.EPeerForgot:
			// 	fmt.Fprintf(sr.out_f, "%d Fg %v\n", time.Now().UnixMilli(), event.PeerID)
		}
	}
}
