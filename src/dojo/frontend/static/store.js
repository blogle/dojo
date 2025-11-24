import { createInitialState, createStore } from "./services/state.js";

export const store = createStore(createInitialState());
