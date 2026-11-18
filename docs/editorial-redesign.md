# Editorial redesign

## Product continuity
The landing page lives at / and Command Center at /command-center. All five other tool URLs remain unchanged. The brand link returns to the story; the header action connects the story and workspace. Six workspace destinations sit in a compact sticky horizontal navigation surface. Narrow screens keep the navigation horizontally scrollable, with native keyboard-accessible links.

Both surfaces use locally bundled Space Grotesk and Inter, the README signal blue, ink, pale blue-grey paper, consistent control shapes, and the same network illustration component. Only the floating navigation uses subtle transparency and blur, explicitly requested in the redesign brief.

## Story and interactions
The landing narrative explains the traffic problem, its consequences, the ML approach, processing stages, six workspace modules, and present limitations. Custom native SVG illustrations show a conceptual topology and a many-records-to-one-finding pipeline. No stock images or external visual assets are used.

NetworkMap is reused on the landing page, Command Center, and Network Pulse. Nodes support pointer, Enter, and Space activation; a native device selector provides a touch-friendly alternative. Selected connections update a polite live explanation. Flow animation pauses on demand, stops outside the viewport, and is omitted for reduced motion.

The processing stages use tab/tabpanel semantics, roving focus, arrow keys, Home, and End. Stage content explicitly distinguishes current CSV validation from planned inference and later-phase capabilities.

## Motion decisions
Marketing scroll reveals serve explanation on a first-visit surface. Motion for React animates opacity and transform with a 650 ms ease-out curve, once per section. Reduced-motion users receive opacity-only 150 ms feedback. Repeated workspace controls use immediate state changes and short CSS feedback rather than scroll entrances. Diagram selection crossfades in 180 ms. The flow marker illustrates direction; it is never a live activity indicator.

## Preserved integration
The FastAPI source, API contracts, SQLite initialization, CORS, validation, and centralized API client are unchanged. Health polling, retry, upload errors, valid-file previews, sample labeling, and model-unavailable states remain functional. Dashboard chart range labels now follow the selected window.

Dashboard charts load on entering Command Center, via a lazy page boundary, rather than being needed by the landing page.

## Validation
Production TypeScript/Vite build, 17 backend tests, and Chrome browser regression tests. Browser checks cover all routes, real valid/invalid CSV uploads, API outage/recovery, SVG selection and pause, process keyboard navigation, reduced motion, and horizontal overflow at 1440, 768, and 390 pixels. Browser automation requires both local servers and the Chrome path configured in frontend/smoke.mjs.

Visual screenshots and machine measurements are under .taste-skill/redesign-landing and .taste-skill/redesign-workspace.
## Subtle finishing pass

The original logo.jpg is preserved byte-for-byte and scaled proportionally (50px header height, 42px on phone). Darken compositing blends its light ground into the warm off-white canvas; the JPEG itself has not been converted to an alpha-transparent image.

A custom, noninteractive SVG topology is concentrated at the page edges. Its nodes and routed links share the network atlas language. A mask fades the paths toward the center, leaving content legible. Two brief signal passes run once and are disabled for reduced motion. SVG paths and masks require no external assets or per-frame JavaScript.

The floating navigation has a translucent surface and a 260ms shared active-state transition. Hover arrows move by 2-3px on fine pointers only. Landing scroll entrances now travel 12px over 520ms; reduced motion uses brief opacity feedback. Typography retains the original font families and brand ink/blue, with refinements to tracking, line height, wrapping, and technical labels.

Verification: production build, existing browser integration suite, responsive visual inspections at 1440, 768, and 390. Inspector has zero failures. Warm canvas is requested by the user; compact dashboard metadata, intentional independent panel heights, and editorial landing title sizes explain remaining style warnings.

## Transparent logo update
The site now references logo-transparent.png, a transparent-background cutout of the original logo produced with imagegen. The original logo.jpg remains available. Normal compositing replaces the previous blend-mode workaround. Browser canvas inspection confirmed a zero-alpha background pixel. Topology opacity is increased from .62 to .9 on desktop and .35 to .58 on phone to make the edge pattern more visible without introducing additional elements. Production build and browser regression suite pass.
