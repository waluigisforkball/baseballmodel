# Waluigi's Forkball ⚾

Personal MLB analytics dashboard for DraftKings DFS and sports betting. Single-file app — no build step, no framework, no dependencies beyond a browser.

## Features

- **Betting mode** — K prop targets, HR/power environments, total bases analysis, hand-adjusted matchup table, edge rankings, heatmap
- **DFS mode** — DK salary CSV upload, lineup optimizer, stack scoring, projections
- **YRFI strip** — first inning run likelihood bar with real linescore data
- Live odds via The Odds API (moneylines, spreads, totals, player props)
- Weather per ballpark via Open-Meteo
- Park factors, handedness splits, bullpen modeling

## Usage

Open the live site, pick a date, and the slate loads automatically.

## Stack

Pure HTML/JS, single `index.html` file. Data sources: MLB Stats API, The Odds API, Open-Meteo.
