import { QueryClient } from "@tanstack/vue-query";

const queryClient = new QueryClient();

if (typeof window !== "undefined") {
	window.dojoQueryClient = queryClient;
}

export default queryClient;
