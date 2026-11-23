"use strict";

/* =========================================================
   TRUTH LENS 1.0 — FRONTEND CONTROLLER
   Backend-compatible response handling
========================================================= */

let historyData = [];
let chartInstances = {};
let latestAnalysis = null;

const $ = (id) => document.getElementById(id);

const COLORS = {
    green: "#238653",
    lightGreen: "#8bc9a1",
    red: "#d96b6b",
    orange: "#e5ae57",
    blue: "#7897c4",
    grey: "#aab5ad",
    purple: "#9b87c9"
};


/* =========================================================
   HELPERS
========================================================= */

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

function number(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
}

function normalizeScore(value) {
    if (value === null || value === undefined || value === "") {
        return null;
    }

    let n = Number(value);

    if (!Number.isFinite(n)) return null;
    if (n > 1) n /= 100;

    return Math.max(0, Math.min(1, n));
}

function percentage(value) {
    const score = normalizeScore(value);

    return score === null
        ? "Not calculated"
        : `${Math.round(score * 100)}%`;
}

function getVerdict(item) {
    return String(
        item?.verdict ??
        item?.final_verdict ??
        item?.result ??
        item?.label ??
        "UNKNOWN"
    ).toUpperCase();
}

function getConfidence(item) {
    return (
        item?.confidence ??
        item?.confidence_score ??
        item?.confidence_percentage ??
        item?.numerical_confidence ??
        null
    );
}


/* =========================================================
   HISTORY DATA NORMALIZATION
========================================================= */

function parseStoredResults(results) {
    if (!results) return {};

    if (typeof results === "string") {
        try {
            return JSON.parse(results);
        } catch {
            console.warn("Could not parse stored analysis results.");
            return {};
        }
    }

    return results;
}


function normalizeAnalysisRecord(raw) {
    const results = parseStoredResults(raw?.results);

    const resultObject =
        results &&
        typeof results === "object" &&
        !Array.isArray(results)
            ? results
            : {};

    const extractedClaims = Array.isArray(raw?.claims)
        ? raw.claims
        : [];

    let verifiedClaims = [];

    /*
       Case 1:
       Full analysis object stored in results.
       Example: results.claims
    */

    if (Array.isArray(resultObject.claims)) {
        verifiedClaims = resultObject.claims;
    }

    /*
       Case 2:
       Results itself is an array of claim results.
    */

    else if (Array.isArray(results)) {
        verifiedClaims = results.map((result, index) => {
            const originalClaim = extractedClaims[index];

            const claimText =
                result?.claim ||
                (typeof originalClaim === "string"
                    ? originalClaim
                    : originalClaim?.claim) ||
                "Claim";

            return {
                ...(typeof result === "object" && result !== null
                    ? result
                    : {}),
                claim: claimText
            };
        });
    }

    /*
       Case 3:
       Claims already contain detailed analysis.
    */

    else if (extractedClaims.some(claim =>
        typeof claim === "object" &&
        claim !== null
    )) {
        verifiedClaims = extractedClaims;
    }

    /*
       Case 4:
       Only raw extracted claim strings exist.
       Do not invent verdicts or evidence.
    */

    return {
        ...raw,

        _normalizedClaims: verifiedClaims,

        bias_analysis:
            raw?.bias_analysis ||
            resultObject.bias_analysis ||
            {},

        fallacy_analysis:
            raw?.fallacy_analysis ||
            resultObject.fallacy_analysis ||
            {},

        input_text:
            raw?.input_text ||
            resultObject.input_text ||
            "",

        provider:
            raw?.provider ||
            resultObject.provider ||
            ""
    };
}


/* =========================================================
   DATA ACCESS HELPERS
========================================================= */

function getClaims(item) {
    if (Array.isArray(item?._normalizedClaims)) {
        return item._normalizedClaims;
    }

    if (Array.isArray(item?.claims)) {
        return item.claims.filter(x =>
            typeof x === "object" && x !== null
        );
    }

    if (Array.isArray(item?.results)) {
        return item.results.filter(x =>
            typeof x === "object" && x !== null
        );
    }

    return [];
}


function getEvidence(item) {
    if (Array.isArray(item?.evidence)) {
        return item.evidence;
    }

    if (Array.isArray(item?.evidence_records)) {
        return item.evidence_records;
    }

    return getClaims(item).flatMap(claim =>
        Array.isArray(claim.evidence)
            ? claim.evidence
            : []
    );
}


function getSources(item) {
    if (Array.isArray(item?.sources)) {
        return item.sources;
    }

    if (Array.isArray(item?.retrieved_sources)) {
        return item.retrieved_sources;
    }

    return [];
}


function getText(item) {
    return (
        item?.claim ??
        item?.text ??
        item?.statement ??
        item?.input_text ??
        item?.original_text ??
        "Untitled investigation"
    );
}


function getDate(item) {
    return (
        item?.created_at ??
        item?.timestamp ??
        item?.date ??
        item?.analyzed_at ??
        ""
    );
}


function getProvider(item) {
    if (item?.provider || item?.ai_provider) {
        return item.provider || item.ai_provider;
    }

    const claims = getClaims(item);

    return claims.find(x =>
        x.provider || x.ai_provider
    )?.provider ||
    claims.find(x => x.ai_provider)?.ai_provider ||
    "Unknown";
}


function getExplanation(item) {
    return (
        item?.explanation ??
        item?.reasoning ??
        item?.summary ??
        "No explanation provided."
    );
}


function getBias(item) {
    return item?.bias_analysis ?? item?.bias ?? {};
}


function getFallacies(item) {
    return item?.fallacy_analysis ?? item?.fallacies ?? {};
}


function getFindings(analysis) {
    return Array.isArray(analysis?.findings)
        ? analysis.findings
        : [];
}


function getBiasFindings(item) {
    return getFindings(getBias(item));
}


function getFallacyFindings(item) {
    return getFindings(getFallacies(item));
}


function formatDate(value) {
    if (!value) return "Unknown";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}


function badge(verdict) {
    const v = String(verdict).toLowerCase();

    let type = "uncertain";

    if (v.includes("support")) {
        type = "supported";
    } else if (v.includes("refut") || v.includes("false")) {
        type = "refuted";
    } else if (v.includes("mixed") || v.includes("partial")) {
        type = "mixed";
    }

    return `
        <span class="badge badge-${type}">
            ${escapeHTML(verdict)}
        </span>
    `;
}


function showEmpty(containerId, message) {
    const element = $(containerId);

    if (element) {
        element.innerHTML = `
            <div class="empty-state">
                ${escapeHTML(message)}
            </div>
        `;
    }
}


function allClaims() {
    return historyData.flatMap(item => getClaims(item));
}


function allEvidence() {
    return historyData.flatMap(item => getEvidence(item));
}


function allSources() {
    return historyData.flatMap(item => getSources(item));
}


function allAnalyses() {
    return historyData;
}


function countVerdict(keyword) {
    return allClaims().filter(item =>
        getVerdict(item).toLowerCase().includes(keyword)
    ).length;
}


function getAnalysisLabel(item) {
    return String(
        item.input_text ||
        item.statement ||
        getClaims(item)[0]?.claim ||
        "Investigation"
    ).slice(0, 50);
}


/* =========================================================
   API
========================================================= */

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,

        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            data.error ||
            data.message ||
            `Request failed (${response.status})`
        );
    }

    return data;
}


/* =========================================================
   NAVIGATION
========================================================= */

function navigate(pageName) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active");
    });

    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("active");
    });

    const page = $(`page-${pageName}`);

    if (!page) return;

    page.classList.add("active");

    const nav = document.querySelector(
        `.nav-item[data-page="${pageName}"]`
    );

    if (nav) {
        nav.classList.add("active");
    }

    const pageTitle = $("pageTitle");

    if (pageTitle) {
        pageTitle.textContent = nav
            ? nav.textContent.trim()
            : pageName.replaceAll("-", " ");
    }

    $("sidebar")?.classList.remove("open");

    const renderers = {
        overview: renderDashboard,
        history: renderHistory,
        "claim-intelligence": renderClaims,
        evidence: renderEvidence,
        sources: renderSources,
        bias: renderBias,
        risk: renderRisk,
        settings: loadHealth
    };

    if (renderers[pageName]) {
        renderers[pageName]();
    }
}


document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
        navigate(item.dataset.page);
    });
});


document.querySelectorAll("[data-go]").forEach(button => {
    button.addEventListener("click", () => {
        navigate(button.dataset.go);
    });
});


$("menuToggle")?.addEventListener("click", () => {
    $("sidebar")?.classList.toggle("open");
});


$("closeHistoryDetail")?.addEventListener("click", () => {
    $("historyDetail")?.classList.add("hidden");
});


/* =========================================================
   HISTORY
========================================================= */

function normalizeHistory(data) {
    if (Array.isArray(data)) {
        return data;
    }

    if (Array.isArray(data?.history)) {
        return data.history;
    }

    if (Array.isArray(data?.analyses)) {
        return data.analyses;
    }

    if (Array.isArray(data?.records)) {
        return data.records;
    }

    if (Array.isArray(data?.results)) {
        return data.results;
    }

    return [];
}


/*
   IMPORTANT FIX:

   /history returns summary records.
   /history/<id> returns the complete analysis.

   The dashboard needs complete records to calculate
   verdicts, evidence, sources, bias and fallacies.
*/

async function loadHistory() {
    try {
        const data = await apiRequest("/history");

        const summaries = normalizeHistory(data);

        const completeHistory = await Promise.all(
            summaries.map(async summary => {
                const id = summary.id ?? summary.analysis_id;

                if (!id) {
                    return normalizeAnalysisRecord(summary);
                }

                try {
                    const detail = await apiRequest(
                        `/history/${encodeURIComponent(id)}`
                    );

                    const record =
                        detail.analysis ||
                        detail.record ||
                        detail;

                    return normalizeAnalysisRecord({
                        ...summary,
                        ...record,
                        id
                    });

                } catch (error) {
                    console.warn(
                        `Could not retrieve analysis ${id}:`,
                        error
                    );

                    return normalizeAnalysisRecord(summary);
                }
            })
        );

        historyData = completeHistory;

        console.log("Truth Lens history loaded:", historyData);
        console.log("Total analyses:", historyData.length);
        console.log("Total claims:", allClaims().length);
        console.log("Total evidence:", allEvidence().length);

        renderDashboard();
        renderHistory();

        const activePage = document.querySelector(".page.active");
        const activeId = activePage?.id?.replace("page-", "");

        const renderers = {
            "claim-intelligence": renderClaims,
            evidence: renderEvidence,
            sources: renderSources,
            bias: renderBias,
            risk: renderRisk
        };

        if (renderers[activeId]) {
            renderers[activeId]();
        }

    } catch (error) {
        console.error("History loading failed:", error);

        historyData = [];

        renderDashboard();
        renderHistory();
    }
}


/* =========================================================
   DASHBOARD
========================================================= */

function renderDashboard() {
    const claims = allClaims();
    const evidence = allEvidence();

    const totalAnalyses = $("totalAnalyses");
    const totalClaims = $("totalClaims");
    const totalSources = $("totalSources");
    const supportedClaims = $("supportedClaims");
    const disputedClaims = $("disputedClaims");
    const aiProvider = $("aiProvider");

    if (totalAnalyses) {
        totalAnalyses.textContent = historyData.length;
    }

    if (totalClaims) {
        totalClaims.textContent = claims.length;
    }

    const uniqueSources = new Set(
        evidence
            .map(x => x.source_url || x.url)
            .filter(Boolean)
    );

    if (totalSources) {
        totalSources.textContent = uniqueSources.size;
    }

    if (supportedClaims) {
        supportedClaims.textContent = countVerdict("support");
    }

    if (disputedClaims) {
        disputedClaims.textContent =
            countVerdict("refut") + countVerdict("mixed");
    }

    const providers = historyData
        .map(getProvider)
        .filter(x => x !== "Unknown");

    if (aiProvider) {
        aiProvider.textContent =
            providers.length
                ? providers[0]
                : "--";
    }

    renderRecentHistory();

    renderVerdictChart();
    renderEvidenceQualityChart();
    renderConfidenceChart();
    renderSourceCredibilityChart();
    renderActivityChart();
    renderRelevanceChart();
    renderBiasChart();
    renderFallacyChart();
    renderPublisherChart();
    renderVerdictTrendChart();
}


/* =========================================================
   CHART ENGINE
========================================================= */

function createChart(id, type, labels, datasets, options = {}) {
    const canvas = $(id);

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    if (chartInstances[id]) {
        chartInstances[id].destroy();
    }

    chartInstances[id] = new Chart(canvas, {
        type,

        data: {
            labels,
            datasets
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    display:
                        type === "doughnut" ||
                        type === "pie",

                    position: "bottom",

                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 17,
                        font: {
                            size: 10
                        }
                    }
                },

                tooltip: {
                    backgroundColor: "#14251b",
                    padding: 11,
                    cornerRadius: 7
                }
            },

            scales: ["doughnut", "pie"].includes(type)
                ? {}
                : {
                    x: {
                        grid: {
                            display: false
                        },

                        ticks: {
                            font: {
                                size: 9
                            }
                        }
                    },

                    y: {
                        beginAtZero: true,

                        grid: {
                            color: "#edf1ed"
                        },

                        ticks: {
                            font: {
                                size: 9
                            }
                        }
                    }
                },

            ...options
        }
    });
}


/* =========================================================
   CHARTS
========================================================= */

function renderVerdictChart() {
    const claims = allClaims();

    const counts = [
        claims.filter(x =>
            getVerdict(x).includes("SUPPORT")
        ).length,

        claims.filter(x =>
            /REFUT|FALSE/.test(getVerdict(x))
        ).length,

        claims.filter(x =>
            /MIXED|PARTIAL/.test(getVerdict(x))
        ).length
    ];

    counts.push(
        claims.length - counts.reduce((a, b) => a + b, 0)
    );

    createChart(
        "verdictChart",
        "doughnut",

        ["Supported", "Refuted", "Mixed", "Uncertain"],

        [{
            data: counts,

            backgroundColor: [
                COLORS.green,
                COLORS.red,
                COLORS.orange,
                COLORS.grey
            ],

            borderWidth: 0
        }],

        {
            cutout: "68%"
        }
    );
}


function renderEvidenceQualityChart() {
    const evidence = allEvidence();

    const direct = evidence.filter(x =>
        String(x.evidence_type).toUpperCase().includes("DIRECT")
    ).length;

    const contextual = evidence.filter(x =>
        String(x.evidence_type).toUpperCase().includes("CONTEXT")
    ).length;

    const weak = evidence.filter(x =>
        String(x.evidence_type).toUpperCase().includes("WEAK")
    ).length;

    createChart(
        "evidenceQualityChart",
        "doughnut",

        ["Direct", "Contextual", "Weak", "Unclassified"],

        [{
            data: [
                direct,
                contextual,
                weak,
                evidence.length - direct - contextual - weak
            ],

            backgroundColor: [
                COLORS.green,
                COLORS.blue,
                COLORS.orange,
                COLORS.grey
            ],

            borderWidth: 0
        }],

        {
            cutout: "68%"
        }
    );
}


function renderConfidenceChart() {
    const claims = allClaims().filter(x =>
        getConfidence(x) !== null
    );

    const recent = claims.slice(-10);

    createChart(
        "confidenceChart",
        "bar",

        recent.map((x, i) => `Claim ${i + 1}`),

        [{
            label: "Confidence %",

            data: recent.map(x =>
                Math.round(
                    normalizeScore(getConfidence(x)) * 100
                )
            ),

            backgroundColor: COLORS.green,
            borderRadius: 5
        }],

        {
            scales: {
                y: {
                    min: 0,
                    max: 100,

                    ticks: {
                        callback: value => value + "%"
                    }
                },

                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    );
}


function renderSourceCredibilityChart() {
    const sources = allEvidence();

    const scores = sources.map(x =>
        normalizeScore(
            x.source_quality_score ??
            x.credibility_score
        )
    ).filter(x => x !== null);

    createChart(
        "sourceCredibilityChart",
        "doughnut",

        ["Higher score", "Moderate score", "Lower score"],

        [{
            data: [
                scores.filter(x => x >= 0.7).length,
                scores.filter(x => x >= 0.4 && x < 0.7).length,
                scores.filter(x => x < 0.4).length
            ],

            backgroundColor: [
                COLORS.green,
                COLORS.orange,
                COLORS.red
            ],

            borderWidth: 0
        }],

        {
            cutout: "68%"
        }
    );
}


function renderActivityChart() {
    const dates = {};

    historyData.forEach(item => {
        const raw = getDate(item);

        if (!raw) return;

        const key = formatDate(raw);

        dates[key] = (dates[key] || 0) + 1;
    });

    const labels = Object.keys(dates).slice(-10);

    createChart(
        "activityChart",
        "line",
        labels,

        [{
            label: "Investigations",

            data: labels.map(x => dates[x]),

            borderColor: COLORS.green,
            backgroundColor: "rgba(35,134,83,0.10)",
            fill: true,
            tension: 0.35,
            pointRadius: 4
        }]
    );
}


function renderRelevanceChart() {
    const evidence = allEvidence().slice(0, 10);

    createChart(
        "relevanceChart",
        "bar",

        evidence.map((x, i) => `Evidence ${i + 1}`),

        [{
            label: "Relevance %",

            data: evidence.map(x => {
                const score = normalizeScore(x.relevance_score);

                return score === null
                    ? 0
                    : Math.round(score * 100);
            }),

            backgroundColor: COLORS.blue,
            borderRadius: 5
        }],

        {
            scales: {
                y: {
                    min: 0,
                    max: 100,

                    ticks: {
                        callback: value => value + "%"
                    }
                },

                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    );
}


function countFindings(type) {
    return historyData.flatMap(item =>
        type === "bias"
            ? getBiasFindings(item)
            : getFallacyFindings(item)
    );
}


function renderBiasChart() {
    const findings = countFindings("bias");
    const values = {};

    findings.forEach(x => {
        const name = x.type || x.name || "Other";

        values[name] = (values[name] || 0) + 1;
    });

    const labels = Object.keys(values);

    createChart(
        "biasChart",
        "bar",
        labels,

        [{
            label: "Detections",

            data: labels.map(x => values[x]),

            backgroundColor: COLORS.purple,
            borderRadius: 5
        }]
    );
}


function renderFallacyChart() {
    const findings = countFindings("fallacy");
    const values = {};

    findings.forEach(x => {
        const name = x.type || x.name || "Other";

        values[name] = (values[name] || 0) + 1;
    });

    const labels = Object.keys(values);

    createChart(
        "fallacyChart",
        "bar",
        labels,

        [{
            label: "Detections",

            data: labels.map(x => values[x]),

            backgroundColor: COLORS.orange,
            borderRadius: 5
        }]
    );
}


function renderPublisherChart() {
    const values = {};

    allEvidence().forEach(item => {
        const name =
            item.publisher ||
            item.publisher_name ||
            "Unknown";

        values[name] = (values[name] || 0) + 1;
    });

    const sorted = Object.entries(values)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 7);

    createChart(
        "publisherChart",
        "bar",

        sorted.map(x => x[0]),

        [{
            label: "Evidence records",

            data: sorted.map(x => x[1]),

            backgroundColor: COLORS.green,
            borderRadius: 5
        }],

        {
            indexAxis: "y",

            scales: {
                x: {
                    beginAtZero: true
                },

                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    );
}


function renderVerdictTrendChart() {
    const recent = historyData.slice(-10);

    const labels = recent.map((x, i) =>
        `Analysis ${i + 1}`
    );

    const supported = [];
    const refuted = [];
    const uncertain = [];

    recent.forEach(item => {
        const claims = getClaims(item);

        supported.push(
            claims.filter(x =>
                getVerdict(x).includes("SUPPORT")
            ).length
        );

        refuted.push(
            claims.filter(x =>
                /REFUT|FALSE/.test(getVerdict(x))
            ).length
        );

        uncertain.push(
            claims.filter(x =>
                !/SUPPORT|REFUT|FALSE|MIXED|PARTIAL/.test(
                    getVerdict(x)
                )
            ).length
        );
    });

    createChart(
        "verdictTrendChart",
        "line",
        labels,

        [
            {
                label: "Supported",
                data: supported,
                borderColor: COLORS.green,
                tension: 0.3
            },

            {
                label: "Refuted",
                data: refuted,
                borderColor: COLORS.red,
                tension: 0.3
            },

            {
                label: "Uncertain",
                data: uncertain,
                borderColor: COLORS.orange,
                tension: 0.3
            }
        ]
    );
}


/* =========================================================
   RECENT HISTORY
========================================================= */

function renderRecentHistory() {
    const body = $("recentHistory");

    if (!body) return;

    const recent = [...historyData].reverse().slice(0, 5);

    if (!recent.length) {
        body.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">
                    No investigations recorded yet.
                </td>
            </tr>
        `;

        return;
    }

    body.innerHTML = recent.map(item => {
        const claim = getClaims(item)[0] || {};

        return `
            <tr>
                <td>${escapeHTML(getAnalysisLabel(item))}</td>

                <td>${badge(getVerdict(claim))}</td>

                <td>${percentage(getConfidence(claim))}</td>

                <td>${escapeHTML(formatDate(getDate(item)))}</td>

                <td>
                    <span class="badge badge-supported">
                        Recorded
                    </span>
                </td>
            </tr>
        `;
    }).join("");
}


/* =========================================================
   CLAIM INTELLIGENCE
========================================================= */

function renderClaims() {
    const claims = allClaims();

    $("claimPageTotal").textContent = claims.length;

    $("claimPageSupported").textContent =
        countVerdict("support");

    $("claimPageRefuted").textContent =
        countVerdict("refut");

    $("claimPageUncertain").textContent =
        claims.filter(x =>
            !/SUPPORT|REFUT|FALSE|MIXED|PARTIAL/.test(
                getVerdict(x)
            )
        ).length;

    if (!claims.length) {
        showEmpty(
            "claimRecords",
            "No claim records available."
        );

        return;
    }

    $("claimRecords").innerHTML = claims.map(item => `
        <div class="record-card">

            <h4>${escapeHTML(getText(item))}</h4>

            <p>${escapeHTML(getExplanation(item))}</p>

            <div class="record-meta">
                ${badge(getVerdict(item))}

                <span>
                    Confidence: ${percentage(getConfidence(item))}
                </span>

                <span>
                    Provider: ${escapeHTML(item.provider || "Unknown")}
                </span>
            </div>

        </div>
    `).join("");
}


/* =========================================================
   EVIDENCE EXPLORER
========================================================= */

function renderEvidence() {
    const evidence = allEvidence();

    const direct = evidence.filter(x =>
        String(x.evidence_type).toUpperCase().includes("DIRECT")
    ).length;

    const contextual = evidence.filter(x =>
        String(x.evidence_type).toUpperCase().includes("CONTEXT")
    ).length;

    const weak = evidence.filter(x =>
        String(x.evidence_type).toUpperCase().includes("WEAK")
    ).length;

    $("evidenceTotal").textContent = evidence.length;
    $("directEvidence").textContent = direct;
    $("contextEvidence").textContent = contextual;
    $("weakEvidence").textContent = weak;

    if (!evidence.length) {
        showEmpty(
            "evidenceRecords",
            "No evidence records available."
        );

        return;
    }

    $("evidenceRecords").innerHTML = evidence.map(item => {
        const title =
            item.source_title ||
            item.title ||
            "Evidence";

        const url =
            item.source_url ||
            item.url ||
            "";

        return `
            <div class="record-card">

                <h4>${escapeHTML(title)}</h4>

                <p>
                    ${escapeHTML(
                        item.sentence ||
                        item.text ||
                        item.snippet ||
                        ""
                    )}
                </p>

                <div class="record-meta">

                    <span>
                        Type: ${escapeHTML(item.evidence_type || "Unclassified")}
                    </span>

                    <span>
                        Relevance: ${percentage(item.relevance_score)}
                    </span>

                    <span>
                        Quality: ${percentage(item.evidence_quality)}
                    </span>

                    ${
                        url
                            ? `<a href="${escapeHTML(url)}"
                                  target="_blank"
                                  rel="noopener noreferrer">
                                  Open source ↗
                               </a>`
                            : ""
                    }

                </div>

            </div>
        `;
    }).join("");
}


/* =========================================================
   SOURCE INTELLIGENCE
========================================================= */

function renderSources() {
    const unique = new Map();

    allEvidence().forEach(item => {
        const url =
            item.source_url ||
            item.url ||
            "";

        const title =
            item.source_title ||
            item.title ||
            "Unknown source";

        unique.set(url || title, item);
    });

    const sources = [...unique.values()];

    $("uniqueSources").textContent = sources.length;

    $("publisherCount").textContent = new Set(
        sources.map(x =>
            x.publisher ||
            x.publisher_name ||
            "Unknown"
        )
    ).size;

    $("domainCount").textContent = new Set(
        sources.map(x =>
            x.publisher_domain ||
            "Unknown"
        )
    ).size;

    if (!sources.length) {
        showEmpty(
            "sourceRecords",
            "No source records available."
        );

        return;
    }

    $("sourceRecords").innerHTML = sources.map(item => {
        const title =
            item.source_title ||
            item.title ||
            "Unknown source";

        const url =
            item.source_url ||
            item.url ||
            "";

        return `
            <div class="record-card">

                <h4>${escapeHTML(title)}</h4>

                <p>
                    ${escapeHTML(
                        item.publisher ||
                        item.publisher_name ||
                        "Publisher unavailable"
                    )}
                </p>

                <div class="record-meta">

                    <span>
                        Source type:
                        ${escapeHTML(item.source_type || item.source_category || "Unknown")}
                    </span>

                    <span>
                        Assessment:
                        ${percentage(item.source_quality_score ?? item.credibility_score)}
                    </span>

                    <span>
                        Transparency:
                        ${percentage(item.article_transparency_score)}
                    </span>

                    <span>
                        Independence:
                        ${escapeHTML(item.source_diversity || "Not assessed")}
                    </span>

                    ${
                        url
                            ? `<a href="${escapeHTML(url)}"
                                  target="_blank"
                                  rel="noopener noreferrer">
                                  Visit source ↗
                               </a>`
                            : ""
                    }

                </div>

            </div>
        `;
    }).join("");
}


/* =========================================================
   BIAS AND FALLACIES
========================================================= */

function renderBias() {
    renderBiasRecords();
    renderBiasDetailCharts();
}


function renderBiasDetailCharts() {
    const biases = countFindings("bias");
    const fallacies = countFindings("fallacy");

    const group = (items) => {
        const values = {};

        items.forEach(x => {
            const name = x.type || x.name || "Other";

            values[name] = (values[name] || 0) + 1;
        });

        return values;
    };

    const biasValues = group(biases);
    const fallacyValues = group(fallacies);

    createChart(
        "biasDetailChart",
        "doughnut",

        Object.keys(biasValues),

        [{
            data: Object.values(biasValues),

            backgroundColor: [
                COLORS.green,
                COLORS.blue,
                COLORS.purple,
                COLORS.orange,
                COLORS.red
            ],

            borderWidth: 0
        }],

        {
            cutout: "62%"
        }
    );

    createChart(
        "fallacyDetailChart",
        "doughnut",

        Object.keys(fallacyValues),

        [{
            data: Object.values(fallacyValues),

            backgroundColor: [
                COLORS.orange,
                COLORS.red,
                COLORS.blue,
                COLORS.purple,
                COLORS.green
            ],

            borderWidth: 0
        }],

        {
            cutout: "62%"
        }
    );
}


function renderBiasRecords() {
    const records = [];

    historyData.forEach(item => {
        getBiasFindings(item).forEach(x => {
            records.push({
                category: "Potential bias",
                item: x
            });
        });

        getFallacyFindings(item).forEach(x => {
            records.push({
                category: "Potential fallacy",
                item: x
            });
        });
    });

    if (!records.length) {
        showEmpty(
            "biasRecords",
            "No bias or fallacy findings detected."
        );

        return;
    }

    $("biasRecords").innerHTML = records.map(record => {
        const item = record.item;

        return `
            <div class="record-card">

                <h4>
                    ${escapeHTML(item.type || item.name || "Finding")}
                </h4>

                <p>
                    ${escapeHTML(
                        item.description ||
                        item.explanation ||
                        "No additional description available."
                    )}
                </p>

                <div class="record-meta">
                    <span>${escapeHTML(record.category)}</span>
                </div>

            </div>
        `;
    }).join("");
}


/* =========================================================
   RISK INTELLIGENCE
========================================================= */

function renderRisk() {
    const claims = allClaims();
    const risks = [];

    claims.forEach(item => {
        const verdict = getVerdict(item);

        if (/UNKNOWN|UNCERTAIN|INSUFFICIENT/.test(verdict)) {
            risks.push({
                title: getText(item),

                reason:
                    "The available evidence does not establish a conclusive verdict.",

                severity: "Review recommended"
            });
        }

        if (/CONFLICT|MIXED/.test(verdict)) {
            risks.push({
                title: getText(item),

                reason:
                    "The evidence assessment indicates conflicting or mixed findings.",

                severity: "Further investigation"
            });
        }

        if (item.verification_error) {
            risks.push({
                title: getText(item),

                reason:
                    "AI verification reported an error.",

                severity: "Verification issue"
            });
        }
    });

    $("riskUncertain").textContent = claims.filter(x =>
        /UNKNOWN|UNCERTAIN/.test(getVerdict(x))
    ).length;

    $("riskInsufficient").textContent = claims.filter(x =>
        getVerdict(x).includes("INSUFFICIENT")
    ).length;

    $("riskConflicts").textContent = claims.filter(x =>
        /CONFLICT|MIXED/.test(getVerdict(x))
    ).length;

    if (!risks.length) {
        showEmpty(
            "riskRecords",
            "No risk flags identified in available records."
        );

        return;
    }

    $("riskRecords").innerHTML = risks.map(item => `
        <div class="record-card">

            <h4>${escapeHTML(item.title)}</h4>

            <p>${escapeHTML(item.reason)}</p>

            <div class="record-meta">
                <span>${escapeHTML(item.severity)}</span>
            </div>

        </div>
    `).join("");
}


/* =========================================================
   HISTORY PAGE
========================================================= */

function renderHistory() {
    const body = $("historyTable");

    if (!body) return;

    if (!historyData.length) {
        body.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">
                    No history available.
                </td>
            </tr>
        `;

        return;
    }

    body.innerHTML = [...historyData].reverse().map(item => {
        const id = item.id ?? item.analysis_id ?? "";

        const claim = getClaims(item)[0] || {};

        return `
            <tr>

                <td>
                    ${escapeHTML(getAnalysisLabel(item))}
                </td>

                <td>
                    ${badge(getVerdict(claim))}
                </td>

                <td>
                    ${percentage(getConfidence(claim))}
                </td>

                <td>
                    ${escapeHTML(formatDate(getDate(item)))}
                </td>

                <td>
                    <button
                        class="text-button"
                        data-history-id="${escapeHTML(id)}"
                    >
                        View report →
                    </button>
                </td>

            </tr>
        `;
    }).join("");

    document.querySelectorAll("[data-history-id]").forEach(button => {
        button.addEventListener("click", () => {
            loadHistoryDetail(button.dataset.historyId);
        });
    });
}


async function loadHistoryDetail(id) {
    if (!id) return;

    try {
        const data = await apiRequest(
            `/history/${encodeURIComponent(id)}`
        );

        const rawItem =
            data.analysis ||
            data.record ||
            data;

        const item = normalizeAnalysisRecord(rawItem);

        const claim = getClaims(item)[0] || {};

        $("historyDetail").classList.remove("hidden");

        $("historyDetailContent").innerHTML = `
            <div class="record-card">

                <h4>
                    ${escapeHTML(getAnalysisLabel(item))}
                </h4>

                ${badge(getVerdict(claim))}

                <p style="margin-top:15px">
                    ${escapeHTML(getExplanation(claim))}
                </p>

                <div class="record-meta">

                    <span>
                        Provider: ${escapeHTML(getProvider(item))}
                    </span>

                    <span>
                        Confidence: ${percentage(getConfidence(claim))}
                    </span>

                </div>

            </div>
        `;

        $("historyDetail").scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {
        alert(
            "Unable to load this report: " + error.message
        );
    }
}


/* =========================================================
   ANALYSIS FORM
========================================================= */

$("claimInput")?.addEventListener("input", event => {
    $("charCount").textContent =
        `${event.target.value.length} characters`;
});


$("analysisForm")?.addEventListener("submit", async event => {
    event.preventDefault();

    const text = $("claimInput").value.trim();

    if (text.length < 10) {
        alert("Please enter a longer statement.");
        return;
    }

    const button = $("analyzeButton");

    button.disabled = true;
    button.textContent = "Analysing...";

    $("analysisLoading").classList.remove("hidden");
    $("analysisResult").classList.add("hidden");

    try {
        const result = await apiRequest("/analyze", {
            method: "POST",

            body: JSON.stringify({
                text
            })
        });

        latestAnalysis = result;

        renderAnalysisResult(result);

        $("analysisResult").classList.remove("hidden");

        await loadHistory();

    } catch (error) {
        alert("Analysis failed: " + error.message);

        console.error(error);

    } finally {
        button.disabled = false;
        button.textContent = "Analyse Statement →";

        $("analysisLoading").classList.add("hidden");
    }
});


/* =========================================================
   ANALYSIS REPORT
========================================================= */

function renderAnalysisResult(data) {
    const claims = getClaims(data);
    const evidence = getEvidence(data);

    const firstClaim = claims[0] || {};

    const verdict = claims.length
        ? getVerdict(firstClaim)
        : "UNKNOWN";

    const explanation = claims.length
        ? getExplanation(firstClaim)
        : "No claim explanation was returned.";

    const provider = getProvider(data);

    const confidence = getConfidence(firstClaim);

    const claimsHTML = claims.length
        ? claims.map(item => `
            <div class="record-card">

                <h4>${escapeHTML(getText(item))}</h4>

                <p>${escapeHTML(getExplanation(item))}</p>

                <div class="record-meta">

                    ${badge(getVerdict(item))}

                    <span>
                        Confidence: ${percentage(getConfidence(item))}
                    </span>

                    <span>
                        Provider: ${escapeHTML(item.provider || "Unknown")}
                    </span>

                </div>

                <p class="muted">
                    ${escapeHTML(item.limitations || "")}
                </p>

            </div>
        `).join("")
        : `
            <p class="muted">
                No separate claim records returned.
            </p>
        `;


    const evidenceHTML = evidence.length
        ? evidence.map(item => `
            <div class="record-card">

                <h4>
                    ${escapeHTML(item.source_title || item.title || "Evidence")}
                </h4>

                <p>
                    ${escapeHTML(
                        item.sentence ||
                        item.text ||
                        item.snippet ||
                        ""
                    )}
                </p>

                <div class="record-meta">

                    <span>
                        Type: ${escapeHTML(item.evidence_type || "Unclassified")}
                    </span>

                    <span>
                        Relevance: ${percentage(item.relevance_score)}
                    </span>

                    <span>
                        Quality: ${percentage(item.evidence_quality)}
                    </span>

                    <span>
                        Publisher: ${escapeHTML(item.publisher || "Unknown")}
                    </span>

                    ${
                        item.source_url || item.url
                            ? `<a href="${escapeHTML(item.source_url || item.url)}"
                                  target="_blank"
                                  rel="noopener noreferrer">
                                  Open source ↗
                               </a>`
                            : ""
                    }

                </div>

            </div>
        `).join("")
        : `
            <p class="muted">
                No evidence records returned.
            </p>
        `;


    const bias = getBias(data);
    const fallacy = getFallacies(data);

    $("analysisResultContent").innerHTML = `
        <div class="record-card">

            <p class="eyebrow">
                FINAL ASSESSMENT
            </p>

            <h2 style="font-size:24px;margin-bottom:12px">
                ${badge(verdict)}
            </h2>

            <h3 style="margin-bottom:8px">
                Confidence: ${percentage(confidence)}
            </h3>

            <p>
                ${escapeHTML(explanation)}
            </p>

            <div class="record-meta">

                <span>
                    AI provider: ${escapeHTML(provider)}
                </span>

                <span>
                    Analysis ID: ${escapeHTML(data.analysis_id ?? "Unknown")}
                </span>

            </div>

            <p class="muted" style="margin-top:12px">
                ${escapeHTML(
                    firstClaim.limitations ||
                    "No additional limitations reported."
                )}
            </p>

        </div>


        <h3 style="margin:22px 0 12px">
            Claim Analysis
        </h3>

        <div class="record-list">
            ${claimsHTML}
        </div>


        <h3 style="margin:22px 0 12px">
            Retrieved Evidence (${evidence.length})
        </h3>

        <div class="record-list">
            ${evidenceHTML}
        </div>


        <h3 style="margin:22px 0 12px">
            Bias Analysis
        </h3>

        <div class="record-card">

            <p>
                ${
                    bias.potential_bias_detected
                        ? "Potential bias detected"
                        : "No potential bias detected"
                }
            </p>

            <p>
                ${escapeHTML(bias.limitations || "")}
            </p>

            <p>
                Findings: ${getBiasFindings(data).length}
            </p>

        </div>


        <h3 style="margin:22px 0 12px">
            Fallacy Analysis
        </h3>

        <div class="record-card">

            <p>
                ${
                    fallacy.potential_fallacies_detected
                        ? "Potential fallacies detected"
                        : "No potential fallacies detected"
                }
            </p>

            <p>
                ${escapeHTML(fallacy.limitations || "")}
            </p>

            <p>
                Findings: ${getFallacyFindings(data).length}
            </p>

        </div>
    `;

    $("analysisResult").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


/* =========================================================
   SYSTEM HEALTH
========================================================= */

async function loadHealth() {
    try {
        const data = await apiRequest("/health");

        $("systemHealth").innerHTML =
            Object.entries(data).map(([key, value]) => `
                <div class="record-card">

                    <h4>
                        ${escapeHTML(
                            key.replaceAll("_", " ").toUpperCase()
                        )}
                    </h4>

                    <p>
                        ${escapeHTML(
                            typeof value === "object"
                                ? JSON.stringify(value)
                                : String(value)
                        )}
                    </p>

                </div>
            `).join("");

    } catch (error) {
        showEmpty(
            "systemHealth",
            "Unable to retrieve system health."
        );

        console.error(error);
    }
}


/* =========================================================
   INITIALIZATION
========================================================= */

document.addEventListener("DOMContentLoaded", async () => {
    await loadHistory();
    await loadHealth();
});