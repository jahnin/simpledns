(function () {
    "use strict";

    const $body = document.querySelector("body");

    /* ------------------------------------------------------------------ */
    /*  Polyfills & helpers                                                */
    /* ------------------------------------------------------------------ */

    /* classList polyfill – © @remy, rem.mit-license.org  */
    !(function () {
        function DOMTokenListShim(el) {
            this.el = el;
            const tokens = el.className.replace(/^\s+|\s+$/g, "").split(/\s+/);
            for (let i = 0; i < tokens.length; i++) push.call(this, tokens[i]);
        }

        function define(obj, prop, getter) {
            Object.defineProperty
                ? Object.defineProperty(obj, prop, { get: getter })
                : obj.__defineGetter__(prop, getter);
        }

        if (!("classList" in document.documentElement)) {
            const proto = Array.prototype;
            const push = proto.push;
            const splice = proto.splice;
            const join = proto.join;

            DOMTokenListShim.prototype = {
                add(token) {
                    if (!this.contains(token)) {
                        push.call(this, token);
                        this.el.className = this.toString();
                    }
                },
                contains(token) {
                    return this.el.className.indexOf(token) !== -1;
                },
                item(i) {
                    return this[i] || null;
                },
                remove(token) {
                    if (this.contains(token)) {
                        for (let i = 0; i < this.length && this[i] !== token; i++);
                        splice.call(this, i, 1);
                        this.el.className = this.toString();
                    }
                },
                toString() {
                    return join.call(this, " ");
                },
                toggle(token) {
                    return this.contains(token) ? this.remove(token) : this.add(token);
                },
            };

            /* expose shim */
            window.DOMTokenList = DOMTokenListShim;
            define(Element.prototype, "classList", function () {
                return new DOMTokenListShim(this);
            });
        }
    })();

    /* canUse – quick feature test */
    window.canUse = function (prop) {
        if (!window._canUse) window._canUse = document.createElement("div");
        const style = window._canUse.style;
        const up = prop.charAt(0).toUpperCase() + prop.slice(1);
        return (
            prop in style ||
            `Moz${up}` in style ||
            `Webkit${up}` in style ||
            `O${up}` in style ||
            `ms${up}` in style
        );
    };

    /* addEventListener polyfill for really old IE */
    (function () {
        if ("addEventListener" in window) return;
        window.addEventListener = function (type, fn) {
            window.attachEvent("on" + type, fn);
        };
    })();

    /* ------------------------------------------------------------------ */
    /*  Initial page‑load animation                                        */
    /* ------------------------------------------------------------------ */

    window.addEventListener("load", () => {
        window.setTimeout(() => $body.classList.remove("is-preload"), 100);
    });

    /* ------------------------------------------------------------------ */
    /*  Background slideshow (assumes $bgs[], settings, pos, lastPos)      */
    /* ------------------------------------------------------------------ */

    (function () {
        /* guard in case globals are missing */
        if (typeof $bgs === "undefined") return;

        $bgs[pos].classList.add("visible", "top");

        if ($bgs.length === 1 || !canUse("transition")) return;

        window.setInterval(() => {
            lastPos = pos;
            pos = (pos + 1) % $bgs.length;

            $bgs[lastPos].classList.remove("top");
            $bgs[pos].classList.add("visible", "top");

            /* hide the old slide half‑way through the delay */
            window.setTimeout(() => {
                $bgs[lastPos].classList.remove("visible");
            }, settings.delay / 2);
        }, settings.delay);
    })();

    /* ------------------------------------------------------------------ */
    /*  “Signup”‑style flash message element used elsewhere                */
    /* ------------------------------------------------------------------ */

    (function () {
        const $form = document.querySelector("#add-form");
        if (!($form && "addEventListener" in $form)) return;

        const $message = document.createElement("span");
        $message.classList.add("message");
        $form.appendChild($message);

        $message._show = (type, text) => {
            $message.textContent = text;
            $message.classList.add(type, "visible");
            setTimeout(() => $message._hide(), 3000);
        };

        $message._hide = () => $message.classList.remove("visible");
    })();

    /* ------------------------------------------------------------------ */
    /*  DNS‑record CRUD + CSV export                                       */
    /* ------------------------------------------------------------------ */

    let allRecords = []; // cached for export

    async function postRecord(body) {
        const r = await fetch("/api/records", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        return r.ok ? "" : (await r.json()).error || "unknown error";
    }

    document.getElementById("add-form").addEventListener("submit", async (e) => {
        e.preventDefault();

        const body = Object.fromEntries(new FormData(e.target).entries());
        const err = await postRecord(body);
        const msgEl = document.getElementById("msg");

        if (!err) {
            msgEl.textContent = "";
            msgEl.style.color = "#1cb495";
            e.target.reset();
            load();
        } else {
            msgEl.textContent = "Error: " + err;
            msgEl.style.color = "#ff2361";
        }
    });

    /* sorting helpers */
    let sortKey = "domain";
    let sortAsc = true;

    const groupByDomain = (records) =>
        records.reduce((acc, r) => ((acc[r.domain] ??= []).push(r), acc), {});

    function render(groups) {
        const wrap = document.getElementById("records-container");
        const exportBox = document.getElementById("export-container");
        wrap.innerHTML = "";

        if (!Object.keys(groups).length) {
            exportBox.style.display = "none";
            return;
        }
        exportBox.style.display = "block";

        Object.keys(groups)
            .sort()
            .forEach((domain) => {
                const section = document.createElement("section");
                section.innerHTML = `
                    <h2>Domain: ${domain}</h2>
                    <table class="simple-dns-table">
                        <thead>
                            <tr>
                                <th data-key="fqdn">FQDN</th>
                                <th data-key="ip">IP Address</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>`;
                const tbody = section.querySelector("tbody");

                groups[domain].forEach((r) => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td>${r.fqdn}</td>
                        <td>${r.ip}</td>
                        <td>
                            <button class="delete" data-fqdn="${r.fqdn}">Delete</button>
                        </td>`;
                    tbody.appendChild(tr);
                });

                wrap.appendChild(section);
            });
    }

    async function load() {
        try {
            const res = await fetch("/api/records");
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

            allRecords = await res.json();
            allRecords.sort(
                (a, b) =>
                    (a[sortKey] > b[sortKey] ? 1 : -1) * (sortAsc ? 1 : -1)
            );
            render(groupByDomain(allRecords));
        } catch (err) {
            document.getElementById(
                "records-container"
            ).innerHTML = `<p style="color:#c33;text-align:center;margin-top:2rem;">
                Error loading records: ${err.message}
            </p>`;
        }
    }
    
    /* export → CSV */
    function exportToCSV() {
        if (!allRecords.length) return showCustomMessage("No records to export.");

        const header = "FQDN,IP Address,Domain\n";
        const rows = allRecords
            .map((r) => `"${r.fqdn}","${r.ip}","${r.domain}"`)
            .join("\n");
        const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
        const link = Object.assign(document.createElement("a"), {
            href: URL.createObjectURL(blob),
            download: `dns_records_${new Date().toISOString().split("T")[0]}.csv`,
            style: "visibility:hidden",
        });
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showCustomMessage(`Exported ${allRecords.length} DNS records to CSV.`);
    }
	window.exportToCSV = exportToCSV;
    document.addEventListener("click", async (e) => {
        if (!e.target.matches("button.delete")) return;

        const fqdn = e.target.dataset.fqdn;
        if (!(await showCustomConfirm(`Delete DNS record for ${fqdn}?`))) return;

        try {
            const res = await fetch(
                "/api/records/" + encodeURIComponent(fqdn),
                { method: "DELETE" }
            );
            res.ok ? load() : showCustomMessage(`Delete failed: ${(await res.json()).error || "Unknown error"}`);
        } catch (err) {
            showCustomMessage("Delete failed: " + err.message);
        }
    });

    /* ------------------------------------------------------------------ */
    /*  Re‑usable modal helpers                                            */
    /* ------------------------------------------------------------------ */

    function showCustomConfirm(msg) {
        return new Promise((resolve) => {
            const modal = document.createElement("div");
            modal.className = "custom-modal";
            modal.innerHTML = `
                <div class="custom-modal-content">
                    <p>${msg}</p>
                    <div class="custom-modal-buttons">
                        <button id="modal-confirm-yes">Yes</button>
                        <button id="modal-confirm-no">No</button>
                    </div>
                </div>`;
            document.body.appendChild(modal);

            document.getElementById("modal-confirm-yes").onclick = () => {
                modal.remove();
                resolve(true);
            };
            document.getElementById("modal-confirm-no").onclick = () => {
                modal.remove();
                resolve(false);
            };
        });
    }

    function showCustomMessage(msg) {
        const modal = document.createElement("div");
        modal.className = "custom-modal";
        modal.innerHTML = `
            <div class="custom-modal-content">
                <p>${msg}</p>
                <div class="custom-modal-buttons">
                    <button id="modal-message-ok">OK</button>
                </div>
            </div>`;
        document.body.appendChild(modal);
        document.getElementById("modal-message-ok").onclick = () => modal.remove();
    }

    /* initial fetch */
    load();
})();
