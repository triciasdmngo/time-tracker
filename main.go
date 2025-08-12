package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"
)

// AppUsage represents time spent on an application
type AppUsage struct {
	Name     string        `json:"name"`
	Duration time.Duration `json:"duration"`
}

// TimeTracker holds our tracking data
type TimeTracker struct {
	Apps       map[string]time.Duration `json:"apps"`
	LastActive string                   `json:"last_active"`
	LastTime   time.Time                `json:"last_time"`
}

// NewTimeTracker creates a new tracker instance
func NewTimeTracker() *TimeTracker {
	return &TimeTracker{
		Apps:     make(map[string]time.Duration),
		LastTime: time.Now(),
	}
}

// GetActiveApp gets the name of the currently active (frontmost) application on macOS
func GetActiveApp() (string, error) {
	// Use AppleScript to get the frontmost application
	script := `tell application "System Events" to get displayed name of first application process whose frontmost is true`

	cmd := exec.Command("osascript", "-e", script)
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get active app: %v", err)
	}

	appName := strings.TrimSpace(string(output))
	if appName == "" {
		return "Unknown", nil
	}

	return appName, nil
}

// Track updates the tracking data
func (tt *TimeTracker) Track() error {
	currentApp, err := GetActiveApp()
	if err != nil {
		return err
	}

	now := time.Now()

	// If we have a previous active app and it's different, add the elapsed time
	if tt.LastActive != "" {
		elapsed := now.Sub(tt.LastTime)
		tt.Apps[tt.LastActive] += elapsed

		// Only log when switching apps to avoid spam
		if currentApp != tt.LastActive {
			fmt.Printf("Switched from %s to %s (spent %v)\n",
				tt.LastActive, currentApp, elapsed.Round(time.Second))
		}
	}

	// Update tracking state
	tt.LastActive = currentApp
	tt.LastTime = now

	return nil
}

// SaveData saves tracking data to a JSON file
func (tt *TimeTracker) SaveData() error {
	data, err := json.MarshalIndent(tt, "", "  ")
	if err != nil {
		return err
	}

	return ioutil.WriteFile("time_data.json", data, 0644)
}

// LoadData loads tracking data from a JSON file
func (tt *TimeTracker) LoadData() error {
	data, err := ioutil.ReadFile("time_data.json")
	if err != nil {
		if os.IsNotExist(err) {
			return nil // File doesn't exist yet, that's OK
		}
		return err
	}

	return json.Unmarshal(data, tt)
}

// PrintBreakdown shows the current time breakdown
func (tt *TimeTracker) PrintBreakdown() {
	fmt.Println("\n=== Time Breakdown ===")

	// Calculate total time
	totalTime := time.Duration(0)
	for _, duration := range tt.Apps {
		totalTime += duration
	}

	if totalTime == 0 {
		fmt.Println("No time tracked yet.")
		return
	}

	// Sort and display apps by time spent
	for app, duration := range tt.Apps {
		percentage := float64(duration) / float64(totalTime) * 100
		fmt.Printf("%-25s: %8v (%5.1f%%)\n",
			app, duration.Round(time.Second), percentage)
	}

	fmt.Printf("\nTotal tracked time: %v\n", totalTime.Round(time.Second))
	fmt.Println("======================")
}

// CheckPermissions verifies that we have necessary permissions on macOS
func CheckPermissions() error {
	// Try to get the active app - this will fail if we don't have accessibility permissions
	_, err := GetActiveApp()
	if err != nil {
		fmt.Println("\n⚠️  Permission Required!")
		fmt.Println("This app needs Accessibility permissions to track active windows.")
		fmt.Println("\nTo fix this:")
		fmt.Println("1. Go to System Preferences > Security & Privacy > Privacy")
		fmt.Println("2. Click on 'Accessibility' in the left sidebar")
		fmt.Println("3. Click the lock icon and enter your password")
		fmt.Println("4. Add this app to the list (or check the box if it's already there)")
		fmt.Println("5. Restart this app")
		return fmt.Errorf("accessibility permissions required")
	}
	return nil
}

func main() {
	fmt.Println("🕐 macOS Time Tracker Starting...")

	// Check for required permissions
	if err := CheckPermissions(); err != nil {
		log.Fatal(err)
	}

	tracker := NewTimeTracker()

	// Load existing data
	if err := tracker.LoadData(); err != nil {
		log.Printf("Error loading data: %v", err)
	}

	fmt.Println("✅ Time tracker is running!")
	fmt.Println("   - Tracking active app every 2 seconds")
	fmt.Println("   - Showing breakdown every 60 seconds")
	fmt.Println("   - Auto-saving every 30 seconds")
	fmt.Println("   - Press Ctrl+C to stop\n")

	// Get initial state
	if err := tracker.Track(); err != nil {
		log.Printf("Error with initial tracking: %v", err)
	}

	// Track every 2 seconds (more responsive)
	trackTicker := time.NewTicker(2 * time.Second)
	defer trackTicker.Stop()

	// Show breakdown every 60 seconds
	breakdownTicker := time.NewTicker(60 * time.Second)
	defer breakdownTicker.Stop()

	// Save data every 30 seconds
	saveTicker := time.NewTicker(30 * time.Second)
	defer saveTicker.Stop()

	for {
		select {
		case <-trackTicker.C:
			if err := tracker.Track(); err != nil {
				log.Printf("Error tracking: %v", err)
			}

		case <-breakdownTicker.C:
			tracker.PrintBreakdown()

		case <-saveTicker.C:
			if err := tracker.SaveData(); err != nil {
				log.Printf("Error saving data: %v", err)
			} else {
				fmt.Printf("💾 Data saved (%s)\n", time.Now().Format("15:04:05"))
			}
		}
	}
}
