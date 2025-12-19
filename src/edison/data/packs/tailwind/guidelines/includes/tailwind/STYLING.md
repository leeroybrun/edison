<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
## 🚨 CRITICAL: TAILWIND CSS V4 SYNTAX

**Complete Guide**: See [TAILWIND_V4_RULES.md](./TAILWIND_V4_RULES.md) - v4 syntax is DIFFERENT from v3!

**Critical v4 Rules** (full details in guide):

1. **CSS Import** (NOT `@tailwind` directives!):
   ```css
   /* globals.css - CORRECT */
   @import "tailwindcss";

   /* ❌ WRONG - v3 syntax doesn't work in v4! */
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```

2. **Always add `font-sans`** to text elements:
   ```tsx
   <h1 className="text-3xl font-bold font-sans">Title</h1>
   <p className="text-base font-sans">Body</p>
   ```

3. **Use arbitrary values** for custom colors:
   ```tsx
   <div className="bg-[#0a0a0a] text-[#e8e8e8] border-[#222222]">
   ```

4. **Clear `.next` cache** after CSS changes:
   ```bash
   rm -rf <framework-cache-dir> && {{fn:ci_command("dev")}}
   ```

5. **PostCSS plugin** (v4 syntax):
   ```javascript
   // postcss.config.mjs
   export default {
     plugins: {
       '@tailwindcss/postcss': {},  // ✅ v4
     },
   }
   ```

6. **Define tokens in @theme**:
   ```css
   @theme {
     --color-surface: oklch(18% 0.02 260);
     --font-sans: "Inter", system-ui, sans-serif;
   }
   ```
   Use the generated classes (e.g., `bg-surface`, `font-sans`) instead of hardcoded values.

**Red Flags** (indicates v3 syntax was used):
- Times New Roman font → Missing `font-sans`
- No spacing/borders → Utilities not applying (clear cache!)
- White backgrounds in dark theme → Wrong color values
<!-- /section: patterns -->
