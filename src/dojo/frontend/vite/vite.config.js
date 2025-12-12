import path from "node:path";
import { fileURLToPath } from "node:url";
import { transformAsync } from "@babel/core";
import istanbul from "babel-plugin-istanbul";
import { createFilter } from "@rollup/pluginutils";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const coveragePlugin = () => {
	const filter = createFilter(
		["**/src/**/*.{js,ts,jsx,tsx,vue}"],
		["node_modules/**"],
	);
	return {
		name: "dojo-babel-coverage",
		enforce: "post",
		async transform(code, id) {
			if (!process.env.CYPRESS_COVERAGE) {
				return null;
			}
			const [filename] = id.split("?");
			if (!filter(filename)) {
				return null;
			}
			const result = await transformAsync(code, {
				plugins: [[istanbul, { cwd: __dirname }]],
				filename,
				sourceMaps: true,
				babelrc: false,
				configFile: false,
			});
			if (!result) {
				return null;
			}
			return {
				code: result.code,
				map: result.map ?? null,
			};
		},
	};
};

export default defineConfig({
	plugins: [vue(), coveragePlugin()],
	root: __dirname,
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	server: {
		proxy: {
			"/api": {
				target: "http://127.0.0.1:8000",
				changeOrigin: true,
			},
			"/static": {
				target: "http://127.0.0.1:8000",
				changeOrigin: true,
			},
		},
	},
	publicDir: path.resolve(__dirname, "../static/public"),
	build: {
		outDir: path.resolve(__dirname, "../static/dist"),
		emptyOutDir: true,
	},
	test: {
		environment: "jsdom",
		globals: true,
	},
});
