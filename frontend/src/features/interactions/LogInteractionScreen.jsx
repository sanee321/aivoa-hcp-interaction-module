// frontend/src/features/interactions/LogInteractionScreen.jsx
import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchHcps, postInteraction } from "./interactionsSlice";
import * as api from "../../api/apiClient";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function LogInteractionScreen() {
  const dispatch = useDispatch();
  const hcps = useSelector((s) => s.interactions.hcps);
  const lastCreated = useSelector((s) => s.interactions.lastCreated);

  const [mode, setMode] = useState("form");
  const [hcpId, setHcpId] = useState("");
  const [formData, setFormData] = useState({ topic: "", materials: "" });
  const [chatText, setChatText] = useState("");
  const [fetchedInteraction, setFetchedInteraction] = useState(null);

  // new UI state for tool results
  const [followups, setFollowups] = useState([]);
  const [trendSummary, setTrendSummary] = useState(null);
  const [loadingFollowups, setLoadingFollowups] = useState(false);
  const [loadingTrend, setLoadingTrend] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    dispatch(fetchHcps());
  }, [dispatch]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    const payload = {
      hcp_id: hcpId ? Number(hcpId) : null,
      rep_id: "rep_santosh",
      mode,
      raw_text: mode === "chat" ? chatText : null,
      form_data: mode === "form" ? formData : null,
    };

    try {
      const res = await dispatch(postInteraction(payload)).unwrap();
      const id = res.id;

      // Poll the backend for processed result
      const poll = setInterval(async () => {
        try {
          const inter = await api.getInteraction(id);
          if (inter && inter.status === "processed") {
            setFetchedInteraction(inter);
            clearInterval(poll);
          }
        } catch (err) {
          // ignore network blips
        }
      }, 800);
    } catch (err) {
      setError("Failed to save interaction. See console for details.");
      console.error(err);
    }
  }

  // Helper to get the interaction id for tool calls
  function currentInteractionId() {
    // prefer fetchedInteraction (processed record), fallback to lastCreated (from slice)
    if (fetchedInteraction && fetchedInteraction.id) return fetchedInteraction.id;
    if (lastCreated && lastCreated.id) return lastCreated.id;
    return null;
  }

  // Tool: Generate Follow-ups
  async function handleGenerateFollowups() {
    setError(null);
    setFollowups([]);
    const interId = currentInteractionId();
    if (!interId) {
      setError("No interaction available. Save an interaction first.");
      return;
    }
    setLoadingFollowups(true);
    try {
      const resp = await fetch(`${API_BASE}/v1/interactions/${interId}/generate_followups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const data = await resp.json();
      setFollowups(data.followups || []);
    } catch (err) {
      console.error(err);
      setError("Failed to generate follow-ups. See console.");
    } finally {
      setLoadingFollowups(false);
    }
  }

  // Tool: HCP Trend Summary
  async function handleTrendSummary() {
    setError(null);
    setTrendSummary(null);
    const hcp = hcpId || (fetchedInteraction && fetchedInteraction.hcp_id) || null;
    if (!hcp) {
      setError("No HCP selected. Select an HCP to get trend summary.");
      return;
    }
    setLoadingTrend(true);
    try {
      const resp = await fetch(`${API_BASE}/v1/hcps/${hcp}/trend_summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const data = await resp.json();
      setTrendSummary(data);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch trend summary. See console.");
    } finally {
      setLoadingTrend(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", padding: 16 }}>
      <h1>Log Interaction</h1>

      <label>
        Mode:{" "}
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="form">Structured Form</option>
          <option value="chat">Conversational Chat</option>
        </select>
      </label>

      <br /><br />

      <label>
        HCP:{" "}
        <select value={hcpId} onChange={(e) => setHcpId(e.target.value)}>
          <option value="">-- Select HCP --</option>
          {hcps.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name} ({h.speciality})
            </option>
          ))}
        </select>
      </label>

      <br /><br />

      <form onSubmit={handleSubmit}>
        {mode === "form" && (
          <>
            <label>
              Topic:{" "}
              <input
                value={formData.topic}
                onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
              />
            </label>
            <br />
            <label>
              Materials:{" "}
              <input
                value={formData.materials}
                onChange={(e) => setFormData({ ...formData, materials: e.target.value })}
              />
            </label>
          </>
        )}

        {mode === "chat" && (
          <textarea
            rows="5"
            cols="80"
            value={chatText}
            onChange={(e) => setChatText(e.target.value)}
            placeholder="Write your conversation notes here..."
          />
        )}

        <br /><br />
        <button type="submit">Save Interaction</button>
      </form>

      <hr />

      <h2>Processed Result</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}

      {fetchedInteraction ? (
        <div>
          <p><b>Summary:</b> {fetchedInteraction.summary}</p>
          <p>
            <b>Topics:</b>{" "}
            {fetchedInteraction.topics && fetchedInteraction.topics.length > 0
              ? fetchedInteraction.topics.join(", ")
              : "None"}
          </p>
          <p><b>Sentiment:</b> {fetchedInteraction.sentiment}</p>
          <p><b>Interaction ID:</b> {fetchedInteraction.id}</p>
        </div>
      ) : (
        <p>No processed interaction yet.</p>
      )}

      <hr />

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 8 }}>
        <button onClick={handleGenerateFollowups} disabled={loadingFollowups}>
          {loadingFollowups ? "Generating..." : "Generate Follow-ups"}
        </button>

        <button onClick={handleTrendSummary} disabled={loadingTrend}>
          {loadingTrend ? "Fetching..." : "Trend Summary (HCP)"}
        </button>

        <div style={{ marginLeft: "auto", fontSize: 12, color: "#666" }}>
          Interaction: <b>{currentInteractionId() || "—"}</b>
        </div>
      </div>

      {followups && followups.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h3>Follow-ups</h3>
          <ol>
            {followups.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ol>
        </div>
      )}

      {trendSummary && (
        <div style={{ marginTop: 12 }}>
          <h3>Trend Summary</h3>
          <p><b>Summary:</b> {trendSummary.trend_summary || trendSummary.summary || "—"}</p>
          <p><b>Topics:</b> {trendSummary.topics && trendSummary.topics.length ? trendSummary.topics.join(", ") : "None"}</p>
        </div>
      )}
    </div>
  );
}
