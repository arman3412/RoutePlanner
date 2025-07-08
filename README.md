# Route Planner

A Python Tkinter-based GUI application that helps you plan an optimal route visiting multiple locations using the Google Maps Routes API. 
It supports minimizing travel time or distance, respects location closing times, and includes stay durations.

---

## Features

- Input a starting location, up to 4 intermediate stops, and an optional ending location.
- Specify closing times and how long you plan to stay at each stop.
- Choose travel mode (Drive, Bicycle, Walk, Transit).
- Minimize total travel time or distance.
- Supports routes that end at the starting location or a different location.
- Displays the best route and estimated arrival time.

---

## Setup

1. Obtain a Google Maps API key with access to the Routes API.
   
2. **Create a `config.py` file** in the project directory with your API key:
    ```python
    API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"
    ```
