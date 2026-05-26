# latcf / stealth

_STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
            ];
            plugins.length = 3;
            return plugins;
        },
    });

    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en'],
    });

    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );

    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };

    if (window.chrome) {
        const original = window.chrome;
        const newChrome = {};
        for (const key of Object.keys(original)) {
            newChrome[key] = original[key];
        }
        newChrome.runtime = {};
        Object.defineProperty(window, 'chrome', { get: () => newChrome });
    } else {
        window.chrome = { runtime: {} };
    }

    const originalToISOString = Date.prototype.toISOString;
    Date.prototype.toISOString = function() {
        const offset = this.getTimezoneOffset();
        const local = new Date(this.getTime() - offset * 60000);
        return originalToISOString.call(local);
    };

    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false,
        }),
    });

    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, attributes) {
        if (type === 'webgl' || type === 'webgl2') {
            const ctx = originalGetContext.call(this, type, attributes);
            if (ctx) {
                const getExt = ctx.getExtension;
                ctx.getExtension = function(name) {
                    if (name === 'WEBGL_debug_renderer_info') {
                        const ext = getExt.call(this, name);
                        if (ext) {
                            Object.defineProperty(ext, 'UNMASKED_VENDOR_WEBGL', { value: 0x9245 });
                            Object.defineProperty(ext, 'UNMASKED_RENDERER_WEBGL', { value: 0x9246 });
                        }
                        return ext;
                    }
                    return getExt.call(this, name);
                };
            }
            return ctx;
        }
        return originalGetContext.call(this, type, attributes);
    };

    const originalAttachShadow = Element.prototype.attachShadow;
    Element.prototype.attachShadow = function(...args) {
        const shadow = originalAttachShadow.apply(this, args);
        shadow.mode = 'open';
        return shadow;
    };

    if (window.HTMLElement.prototype.hasOwnProperty('offsetHeight')) {
        const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
        Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
            get() {
                const val = originalOffsetHeight.get.call(this);
                return val === 0 ? 1 : val;
            },
        });
    }

    const originalToString = Function.prototype.toString;
    Function.prototype.toString = function() {
        if (this === window.navigator.permissions.query) {
            return 'function query() { [native code] }';
        }
        return originalToString.call(this);
    };
}
"""

_LAUNCH_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-features=IsolateOrigins,site-per-process',
    '--disable-infobars',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    '--disable-component-update',
    '--disable-domain-reliability',
    '--disable-ipc-flooding-protection',
]


def get_stealth_js():
    return _STEALTH_JS


def get_launch_args():
    return list(_LAUNCH_ARGS)


async def apply_stealth(context):
    await context.add_init_script(_STEALTH_JS)
