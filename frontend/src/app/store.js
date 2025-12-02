import { configureStore } from "@reduxjs/toolkit";
import interactionsReducer from "../features/interactions/interactionsSlice";

export const store = configureStore({
  reducer: {
    interactions: interactionsReducer,
  },
});
