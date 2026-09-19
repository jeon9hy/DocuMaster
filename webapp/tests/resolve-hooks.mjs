import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const SRC = fileURLToPath(new URL("../src/", import.meta.url));
const EXTENSIONS = [".ts", ".tsx", "/index.ts"];

function withExtension(path) {
  if (existsSync(path) && !path.endsWith("/") && /\.[cm]?[jt]sx?$/.test(path)) return path;
  return EXTENSIONS.map((ext) => path + ext).find((candidate) => existsSync(candidate));
}

export async function resolve(specifier, context, next) {
  if (specifier.startsWith("@/")) {
    const found = withExtension(SRC + specifier.slice(2));
    if (found) return next(pathToFileURL(found).href, context);
  }
  if (specifier.startsWith(".") && !context.parentURL?.includes("/node_modules/")) {
    const found = withExtension(fileURLToPath(new URL(specifier, context.parentURL)));
    if (found) return next(pathToFileURL(found).href, context);
  }
  return next(specifier, context);
}
