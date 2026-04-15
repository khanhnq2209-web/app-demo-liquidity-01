## 3. UI Architecture & Interactive Components (ECharts Edition)

### 3.1 Global Interaction Logic (Session State)
The app must use `st.session_state` to manage **Cross-Filtering**:
1.  **`selected_entity`**: Stores the ID of the entity clicked in any graph.
2.  **`selected_client_group`**: Stores the ID of the client group clicked in heatmaps.
3.  **`view_mode`**: Stores current hierarchy level.

*Behavior:*
- When a user clicks a node in the **Ownership Graph**, `selected_entity` updates.
- The **Sidebar Filter** automatically updates to reflect this selection.
- All charts re-render filtered to this entity.
- A "Reset Filters" button clears the session state.

---

### 3.2 Main Dashboard Tabs (ECharts Specs)

#### Tab 1: Overview (Executive Summary)
**Layout:**
1.  **KPI Cards Row**:
    - Total Cash | Total Ext AR | Total IC AR | Total IC Loans | Top 1 AR Share % | HHI
2.  **Liquidity Distribution Chart**:
    - **Chart Type:** ECharts Bar Chart.
    - **Interaction:** `on_click` event captures the clicked bar’s entity ID → Updates `selected_entity`.
3.  **AR Concentration Heatmap**:
    - **Chart Type:** ECharts Heatmap.
    - **Interaction:** `on_click` captures row/col indices → Identifies Company & Client Group → Filters Exposure Tab.
4.  **Risk Table**:
    - **Interaction:** Clicking a row sets `selected_entity`.

#### Tab 2: Relationships (Ownership & IC Network)
**Library:** `streamlit-echarts` with `graph` series.

**Layout:**
1.  **Graph Controls**:
    - Slider: "Min Edge Weight" (Filter edges dynamically).
    - Toggle: "Show Ownership" | "Show IC Loans" | "Show IC AR".
    - Button: "Reset Layout".
2.  **Interactive Graph (ECharts Graph Series)**:
    - **Layout:** `force` (Force-directed layout).
    - **Nodes:**
        - `symbolSize`: Proportional to Cash or Total Assets.
        - `color`: Coded by Sub-holding (A/B).
        - `label`: Show name if node is large enough.
    - **Edges:**
        - `lineStyle.width`: Proportional to Ownership % or Loan Amount.
        - `curveness`: 0.1 (Slight curve for clarity).
    - **Interaction:**
        - **Hover:** Rich Tooltip (Name, Cash, AR, Debt, Parent).
        - **Click:** `on_click` event → Sets `selected_entity` → Triggers global filter.
        - **Drag/Zoom:** Native ECharts zoom/pan enabled.
3.  **Side Panel (Contextual)**:
    - When a node is clicked, show a mini-profile:
        - "Selected: [Entity Name]"
        - "Parent: [Parent Name]"
        - "Top 3 IC Partners: [List]"

#### Tab 3: Exposure (External AR)
**Layout:**
1.  **Concentration Heatmap**:
    - **Chart Type:** ECharts Heatmap.
    - **Axes:** X=Client Groups, Y=Companies.
    - **VisualMap:** Color scale (Blue → Red) for AR Amount.
    - **Interaction:** Click cell → Filter dashboard to that Company-Client pair.
2.  **Treemap (Alternative View)**:
    - **Chart Type:** ECharts Treemap.
    - **Hierarchy:** Sub-holding → Company → Client Group.
    - **Interaction:** Click segment to drill down.
3.  **Top 5 Client Bar Chart**:
    - **Chart Type:** ECharts Bar.
    - **Interaction:** Click bar → Filter Intercompany Tab.

#### Tab 4: Intercompany (Internal Plumbing)
**Layout:**
1.  **Sankey Diagram**:
    - **Chart Type:** ECharts Sankey.
    - **Nodes:** Entities.
    - **Links:** IC Loans/AR flows.
    - **Interaction:**
        - `on_click` on a link → Captures `source` and `target` IDs.
        - Updates `selected_pair` in session state.
        - Highlights the specific row in the Table below.
2.  **Pair Exposure Table**:
    - **Library:** Streamlit Dataframe.
    - **Interaction:** Click row → Highlight corresponding link in Sankey (via `selected_pair`).
3.  **Network Graph (Alternative)**:
    - Same as Tab 2, but filtered to show only IC relationships.

---

## 5. Implementation Steps for Developer (ECharts Focus)

1.  **Setup & State Management**:
    - Initialize `st.session_state` for `selected_entity`, `selected_client`, `filters`.
    - Create `callbacks.py` to handle `on_click` events from ECharts.

2.  **ECharts Option Builders**:
    - Create `echart_options.py`:
        - `get_ownership_graph_option(data, selected_entity)`: Returns JSON dict for `st_echarts`.
        - `get_sankey_option(data)`: Returns JSON dict for Sankey.
        - `get_heatmap_option(data)`: Returns JSON dict for Heatmap.
    - *Note:* ECharts options are Python dictionaries that mirror the JSON structure.

3.  **Tab 2 (Relationships) - The Core Visual**:
    - Implement `st_echarts(options=..., on_click=handle_click)`.
    - In `handle_click`, parse the clicked node’s `name` or `id` and update `st.session_state.selected_entity`.
    - Use `st.rerun()` to refresh the dashboard with the new filter.

4.  **Tab 4 (Sankey Interaction)**:
    - Build Sankey option.
    - Implement `on_click` to capture `source` and `target` of the clicked link.
    - Filter the Pair Exposure Table based on this pair.

5.  **Performance Optimization**:
    - Cache ECharts option generation (`@st.cache_data`).
    - Ensure node/edge data is pre-aggregated before passing to ECharts to keep the JSON payload small.

---

## 6. Required Libraries (Updated)

```text
streamlit
pandas
streamlit-echarts  # Primary visualization library
numpy