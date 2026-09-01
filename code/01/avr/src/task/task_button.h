#pragma once

// Called when the button pin reported an edge; restarts the debounce count.
void task_button_process_edge(void);

// Called once per RTC tick; advances the debounce count.
void task_button_process_tick(void);
