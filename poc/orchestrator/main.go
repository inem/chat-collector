// orchestrator — the spine's read side. Knows NOTHING about services either.
// Tails the stream, fans every record to every plugged reader's stdin.
// Readers are any executable in the catalog dir.
//
//	orchestrator <stream.jsonl> <catalog-dir>
package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
)

type reader struct {
	name string
	cmd  *exec.Cmd
	in   io.WriteCloser
}

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintln(os.Stderr, "usage: orchestrator <stream.jsonl> <catalog-dir>")
		os.Exit(1)
	}
	streamPath, catalogDir := os.Args[1], os.Args[2]

	// plug in every executable reader in the catalog
	entries, _ := os.ReadDir(catalogDir)
	var readers []reader
	for _, e := range entries {
		p := filepath.Join(catalogDir, e.Name())
		fi, err := os.Stat(p)
		if err != nil || fi.IsDir() || fi.Mode()&0111 == 0 {
			continue
		}
		cmd := exec.Command(p)
		cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
		in, _ := cmd.StdinPipe()
		if err := cmd.Start(); err != nil {
			fmt.Fprintf(os.Stderr, "[orch] failed to start %s: %v\n", e.Name(), err)
			continue
		}
		readers = append(readers, reader{e.Name(), cmd, in})
		fmt.Fprintf(os.Stderr, "[orch] reader up: %s\n", e.Name())
	}

	// fan every stream record to every reader
	f, err := os.Open(streamPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[orch] cannot open stream: %v\n", err)
		os.Exit(1)
	}
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1024*1024), 64*1024*1024) // records carry bodies — allow big lines
	n := 0
	for sc.Scan() {
		line := sc.Bytes()
		for _, r := range readers {
			r.in.Write(line)
			r.in.Write([]byte("\n"))
		}
		n++
	}
	fmt.Fprintf(os.Stderr, "[orch] fanned %d records to %d readers\n", n, len(readers))

	for _, r := range readers {
		r.in.Close()
	}
	for _, r := range readers {
		r.cmd.Wait()
	}
}
