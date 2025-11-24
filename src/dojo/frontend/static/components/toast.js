import { selectors } from "../constants.js";

export const showToast = (message) => {
  const stack = document.querySelector(selectors.toastStack);
  if (!stack || !message) {
    return;
  }
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  stack.appendChild(toast);
  window.setTimeout(() => {
    toast.remove();
  }, 6000);
};
