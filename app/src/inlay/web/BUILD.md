# Local Mermaid bundle

Mermaid 12.0.0. Bundled with esbuild; the exact dependency tree is in
`build-package-lock.json`. `MERMAID-LICENSE` and `mermaid.js.LEGAL.txt`
accompany the bundle. No npm, CDN or Node process is needed at runtime.

To reproduce in a temporary build directory:

```sh
cp /path/to/inlay/app/src/inlay/web/build-package-lock.json package-lock.json
node -e 'const fs=require("fs"); const l=require("./package-lock.json"); fs.writeFileSync("package.json", JSON.stringify(l.packages[""], null, 2))'
npm ci --ignore-scripts
printf 'import mermaid from "mermaid"; window.mermaid = mermaid;\n' > entry.js
node_modules/.bin/esbuild entry.js --bundle --minify --format=iife --legal-comments=external --outfile=mermaid.js
```

Copy both generated files into this directory. The host page uses strict Mermaid
security, disables HTML labels for portable SVG-to-PNG export, and blocks network
requests. Node shapes that require external icons/assets are not bundled.
