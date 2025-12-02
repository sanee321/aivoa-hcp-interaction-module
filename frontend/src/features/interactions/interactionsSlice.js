import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import * as api from "../../api/apiClient";

export const fetchHcps = createAsyncThunk("interactions/fetchHcps", async () => {
  return api.listHcps();
});

export const postInteraction = createAsyncThunk("interactions/postInteraction", async (payload) => {
  return api.createInteraction(payload);
});

export const fetchInteraction = createAsyncThunk("interactions/fetchInteraction", async (id) => {
  return api.getInteraction(id);
});

const interactionsSlice = createSlice({
  name: "interactions",
  initialState: {
    hcps: [],
    status: "idle",
    lastCreated: null,
    current: null,
    list: [],
    error: null,
  },
  reducers: {
    setCurrent(state, action) {
      state.current = action.payload;
    },
    clearCurrent(state) {
      state.current = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHcps.fulfilled, (state, action) => {
        state.hcps = action.payload;
      })
      .addCase(postInteraction.fulfilled, (state, action) => {
        state.lastCreated = action.payload;
      })
      .addCase(fetchInteraction.fulfilled, (state, action) => {
        state.current = action.payload;
      });
  },
});

export const { setCurrent, clearCurrent } = interactionsSlice.actions;
export default interactionsSlice.reducer;
