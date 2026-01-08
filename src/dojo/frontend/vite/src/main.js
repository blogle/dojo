import { VueQueryPlugin } from "@tanstack/vue-query";
import { createApp } from "vue";
import App from "./App.vue";
import queryClient from "./queryClient";
import router from "./router";

import "../../static/styles/base.css";
import "../../static/styles/layout.css";
import "../../static/styles/forms.css";
import "../../static/styles/ledger.css";
import "../../static/styles/components/transactions.css";
import "../../static/styles/components/accounts.css";
import "../../static/styles/components/allocations.css";
import "../../static/styles/components/budgets.css";
import "../../static/styles/components/transfers.css";
import "../../static/styles/components/investments.css";
import "../../static/styles/components/modals.css";
import "../../static/styles/components/toast.css";

const app = createApp(App);

app.use(router);
app.use(VueQueryPlugin, { queryClient });

app.mount("#app");
