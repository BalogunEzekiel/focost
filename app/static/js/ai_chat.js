// ==========================================================
// ELEMENT REFERENCES
// ==========================================================

const aiButton = document.getElementById("aiCoachButton");

const aiWindow = document.getElementById("aiCoachWindow");

const chatHeader = document.getElementById("chatHeader");

const minimizeBtn = document.getElementById("minimizeAI");

const maximizeBtn = document.getElementById("maximizeAI");

const closeBtn = document.getElementById("closeAI");

const sendBtn = document.getElementById("sendAI");

const input = document.getElementById("chatInput");

const messages = document.getElementById("chatMessages");

// ==========================================================
// WINDOW STATE
// ==========================================================

let isDragging = false;

let isMaximized = false;

let isMinimized = false;

let offsetX = 0;

let offsetY = 0;

let previousState = {};

// ==========================================================
// RESTORE SAVED WINDOW STATE
// ==========================================================

const savedDisplay = localStorage.getItem("ai_display");

if (savedDisplay === "open") {

    aiWindow.style.display = "flex";

}

const savedLeft = localStorage.getItem("ai_left");

const savedTop = localStorage.getItem("ai_top");

if (savedLeft && savedTop) {

    aiWindow.style.left = savedLeft;

    aiWindow.style.top = savedTop;

    aiWindow.style.right = "auto";

    aiWindow.style.bottom = "auto";

}

const savedWidth = localStorage.getItem("ai_width");

const savedHeight = localStorage.getItem("ai_height");

if (savedWidth) {

    aiWindow.style.width = savedWidth;

}

if (savedHeight) {

    aiWindow.style.height = savedHeight;

}

// Restore minimized state

if (

    localStorage.getItem("ai_minimized") === "true"

) {

    aiWindow.classList.add("minimized");

    isMinimized = true;

    minimizeBtn.innerHTML =

        '<i class="bi bi-plus-lg"></i>';

}

// Restore maximized state

if (

    localStorage.getItem("ai_maximized") === "true"

) {

    aiWindow.classList.add("maximized");

    isMaximized = true;

    maximizeBtn.innerHTML =

        '<i class="bi bi-fullscreen-exit"></i>';

}

// ==========================================================
// OPEN / CLOSE WINDOW
// ==========================================================

function openWindow() {

    aiWindow.style.display = "flex";

    localStorage.setItem(

        "ai_display",

        "open"

    );

    if (isMinimized) {

        restoreWindow();

    }

    input.focus();

}

function closeWindow() {

    aiWindow.style.display = "none";

    localStorage.setItem(

        "ai_display",

        "closed"

    );

    if (isMinimized) {

        restoreWindow();

    }

}

// ==========================================================
// MINIMIZE / RESTORE
// ==========================================================

function minimizeWindow() {

    aiWindow.classList.add("minimized");

    isMinimized = true;

    minimizeBtn.innerHTML =

        '<i class="bi bi-plus-lg"></i>';

    localStorage.setItem(

        "ai_minimized",

        "true"

    );

}

function restoreWindow() {

    aiWindow.classList.remove("minimized");

    isMinimized = false;

    minimizeBtn.innerHTML =

        '<i class="bi bi-dash-lg"></i>';

    localStorage.setItem(

        "ai_minimized",

        "false"

    );

}

// ==========================================================
// MAXIMIZE / RESTORE
// ==========================================================

function maximizeWindow() {

    if (isMaximized) return;

    previousState = {

        left: aiWindow.style.left,

        top: aiWindow.style.top,

        right: aiWindow.style.right,

        bottom: aiWindow.style.bottom,

        width: aiWindow.style.width,

        height: aiWindow.style.height

    };

    aiWindow.classList.add("maximized");

    isMaximized = true;

    maximizeBtn.innerHTML =

        '<i class="bi bi-fullscreen-exit"></i>';

    localStorage.setItem(

        "ai_maximized",

        "true"

    );

}

function restoreMaximizedWindow() {

    aiWindow.classList.remove("maximized");

    aiWindow.style.left = previousState.left;

    aiWindow.style.top = previousState.top;

    aiWindow.style.right = previousState.right;

    aiWindow.style.bottom = previousState.bottom;

    aiWindow.style.width = previousState.width;

    aiWindow.style.height = previousState.height;

    isMaximized = false;

    maximizeBtn.innerHTML =

        '<i class="bi bi-square"></i>';

    localStorage.setItem(

        "ai_maximized",

        "false"

    );

}

// ==========================================================
// DRAG WINDOW
// ==========================================================

chatHeader.addEventListener("mousedown", function (e) {

    if (isMaximized) return;

    isDragging = true;

    const rect = aiWindow.getBoundingClientRect();

    offsetX = e.clientX - rect.left;

    offsetY = e.clientY - rect.top;

    document.body.style.userSelect = "none";

});


document.addEventListener("mousemove", function (e) {

    if (!isDragging) return;

    const left = e.clientX - offsetX;

    const top = e.clientY - offsetY;

    aiWindow.style.left = left + "px";

    aiWindow.style.top = top + "px";

    aiWindow.style.right = "auto";

    aiWindow.style.bottom = "auto";

});


document.addEventListener("mouseup", function () {

    if (!isDragging) return;

    isDragging = false;

    document.body.style.userSelect = "";

    localStorage.setItem(

        "ai_left",

        aiWindow.style.left

    );

    localStorage.setItem(

        "ai_top",

        aiWindow.style.top

    );

});

// ==========================================================
// FINANCIAL CARD RENDERER
// ==========================================================

function renderFinancialCards(text) {

    if (!text)
        return null;

    //----------------------------------------------------------
    // Extract Card Type
    //----------------------------------------------------------

    const match = text.match(/^\[(.*?)\]/);

    if (!match)
        return null;

    const type = match[1];

    let payload;

    try {

        payload = JSON.parse(

            text.replace(match[0], "")

        );

    }

    catch {

        return null;

    }

    //----------------------------------------------------------
    // CARD ROUTER
    //----------------------------------------------------------

    switch (type) {

        case "BALANCE_CARD":
            return balanceCard(payload);

        case "INCOME_CARD":
            return incomeCard(payload);

        case "EXPENSE_CARD":
            return expenseCard(payload);

        case "BUDGET_CARD":
            return budgetCard(payload);

        case "GOAL_CARD":
            return goalCard(payload);

        case "HEALTH_CARD":
            return healthCard(payload);

        case "FORECAST_CARD":
            return forecastCard(payload);

        case "SPENDING_CARD":
            return spendingCard(payload);

        case "TOP_CATEGORY_CARD":
            return topCategoryCard(payload);

        case "TOP_MERCHANT_CARD":
            return topMerchantCard(payload);

        case "CASHFLOW_CARD":
            return cashflowCard(payload);

        case "INSIGHT_CARD":
            return insightCard(payload);

        case "RECOMMENDATION_CARD":
            return recommendationCard(payload);

        case "TABLE_CARD":
            return tableCard(payload);

        case "SUCCESS_CARD":
            return statusCard(payload, "success");

        case "WARNING_CARD":
            return statusCard(payload, "warning");

        case "ERROR_CARD":
            return statusCard(payload, "danger");

        default:
            return null;

    }

}

// ==========================================================
// HELPER FUNCTIONS
// ==========================================================

function money(value){

    return "₦" + Number(value).toLocaleString();

}

function percent(value){

    return Number(value).toFixed(1) + "%";

}

function badge(color,text){

    return `
        <span class="badge bg-${color}">
            ${text}
        </span>
    `;

}

// ==========================================================
// BALANCE CARD
// ==========================================================

function balanceCard(d){

return `

<div class="finance-card">

<div class="finance-header">

<h5>Available Balance</h5>

</div>

<div class="finance-big">

${money(d.balance)}

</div>

<div class="finance-grid">

<div>

<small>Income</small>

<h6>${money(d.income)}</h6>

</div>

<div>

<small>Expenses</small>

<h6>${money(d.expense)}</h6>

</div>

</div>

</div>

`;

}

// ==========================================================
// INCOME CARD
// ==========================================================

function incomeCard(d){

return `

<div class="finance-card">

<h5>Total Income</h5>

<div class="finance-big">

${money(d.total)}

</div>

<p>

Source:

<strong>${d.source||"All Sources"}</strong>

</p>

</div>

`;

}

// ==========================================================
// EXPENSE CARD
// ==========================================================

function expenseCard(d){

return `

<div class="finance-card">

<h5>Total Expenses</h5>

<div class="finance-big text-danger">

${money(d.total)}

</div>

<p>

Category:

<strong>${d.category||"All Categories"}</strong>

</p>

</div>

`;

}

// ==========================================================
// BUDGET CARD
// ==========================================================

function budgetCard(d){

return `

<div class="finance-card">

<h5>

Budget

</h5>

<div>

Used

${percent(d.used)}

</div>

<div class="progress">

<div

class="progress-bar"

style="width:${d.used}%">

</div>

</div>

<br>

Remaining

<strong>

${money(d.remaining)}

</strong>

</div>

`;

}

// ==========================================================
// GOAL CARD
// ==========================================================

function goalCard(d){

return `

<div class="finance-card">

<h5>

${d.goal}

</h5>

<div class="progress">

<div

class="progress-bar bg-success"

style="width:${d.progress}%">

</div>

</div>

<p>

${percent(d.progress)} Complete

</p>

<p>

Saved

${money(d.saved)}

of

${money(d.target)}

</p>

</div>

`;

}

// ==========================================================
// HEALTH CARD
// ==========================================================

function healthCard(d){

return `

<div class="finance-card">

<h5>

Financial Health

</h5>

<div class="finance-big">

${d.score}/100

</div>

${badge(

d.score>=80?

"success":

d.score>=60?

"warning":

"danger",

d.status

)}

</div>

`;

}

// ==========================================================
// FORECAST CARD
// ==========================================================

function forecastCard(d){

return `

<div class="finance-card">

<h5>

Forecast

</h5>

<div class="finance-big">

${money(d.balance)}

</div>

Projected Month-End Balance

</div>

`;

}

// ==========================================================
// SEPNDING CARD
// ==========================================================

function spendingCard(d){

return `

<div class="finance-card">

<h5>

Highest Spending

</h5>

<div class="finance-big">

${d.category}

</div>

${money(d.amount)}

</div>

`;

}

// ==========================================================
// TOP CATEGORY CARD
// ==========================================================

function topCategoryCard(d){

return `

<div class="finance-card">

<h5>

Top Category

</h5>

<div class="finance-big">

${d.category}

</div>

${money(d.total)}

</div>

`;

}

// ==========================================================
// TOP MERCHANT CARD
// ==========================================================

function topMerchantCard(d){

return `

<div class="finance-card">

<h5>

Top Merchant

</h5>

<div class="finance-big">

${d.merchant}

</div>

${money(d.total)}

</div>

`;

}

// ==========================================================
// CASH FLOW CARD
// ==========================================================

function cashflowCard(d){

return `

<div class="finance-card">

<h5>

Cash Flow

</h5>

<div class="finance-grid">

<div>

In

<h6>

${money(d.income)}

</h6>

</div>

<div>

Out

<h6>

${money(d.expense)}

</h6>

</div>

</div>

</div>

`;

}

// ==========================================================
// INSIGHT CARD
// ==========================================================

function insightCard(d){

return `

<div class="finance-card">

<h5>

AI Insight

</h5>

<p>

${d.message}

</p>

</div>

`;

}

// ==========================================================
// RECOMMENDATION CARD
// ==========================================================

function recommendationCard(d){

return `

<div class="finance-card">

<h5>

Recommendation

</h5>

<p>

${d.message}

</p>

</div>

`;

}

// ==========================================================
// TABLE CARD
// ==========================================================

function tableCard(d){

let rows="";

d.rows.forEach(r=>{

rows+=`

<tr>

<td>${r.name}</td>

<td>${money(r.amount)}</td>

</tr>

`;

});

return `

<div class="finance-card">

<h5>

Summary

</h5>

<table class="table table-sm">

<thead>

<tr>

<th>Name</th>

<th>Amount</th>

</tr>

</thead>

<tbody>

${rows}

</tbody>

</table>

</div>

`;

}

// ==========================================================
// STATUS CARD
// ==========================================================

function statusCard(d,color){

return `

<div class="alert alert-${color}">

<strong>

${d.title}

</strong>

<br>

${d.message}

</div>

`;

}

// ==========================================================
// MARKDOWN RENDERER
// ==========================================================

// ==========================================================
// MARKDOWN RENDERER
// ==========================================================

function renderMarkdown(text) {

    if (!text)
        return "";

    marked.setOptions({

        gfm: true,

        breaks: true

    });

    return marked.parse(text);

}

// ==========================================================
// APPEND MESSAGE
// ==========================================================

function appendMessage(sender, text, role) {

    // ------------------------------------------------------
    // Outer message row
    // ------------------------------------------------------

    const row = document.createElement("div");

    row.className =
        role === "user"
            ? "message user"
            : "message assistant";


    // ------------------------------------------------------
    // Message bubble
    // ------------------------------------------------------

    const bubble = document.createElement("div");

    bubble.className =
        role === "user"
            ? "user-message"
            : "ai-message";


    // ------------------------------------------------------
    // Sender header
    // ------------------------------------------------------

    const senderDiv = document.createElement("div");

    senderDiv.className = "message-sender";


    if (role === "assistant") {

        senderDiv.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <strong>FOCOST AI</strong>

                <span class="small text-success">
                    ● Online
                </span>
            </div>
        `;

    } else {

        // Sender is plain text for user messages.
        // textContent prevents accidental HTML injection.

        senderDiv.textContent = sender || "You";

    }


    // ------------------------------------------------------
    // Message body
    // ------------------------------------------------------

    const body = document.createElement("div");

    body.className = "message-body";


    // ------------------------------------------------------
    // Financial card detection
    // ------------------------------------------------------

    const financial = renderFinancialCards(text);


    if (financial) {

        body.innerHTML = financial;

    } else {

        body.innerHTML = renderMarkdown(text);

    }


    // ------------------------------------------------------
    // Syntax highlighting
    // ------------------------------------------------------

    if (
        typeof hljs !== "undefined"
    ) {

        body
            .querySelectorAll("pre code")
            .forEach(block => {

                try {

                    hljs.highlightElement(block);

                } catch (error) {

                    console.warn(
                        "Syntax highlighting failed:",
                        error
                    );

                }

            });

    }


    // ------------------------------------------------------
    // Assemble message
    // ------------------------------------------------------

    bubble.appendChild(senderDiv);

    bubble.appendChild(body);

    row.appendChild(bubble);

    messages.appendChild(row);


    // ------------------------------------------------------
    // Scroll
    // ------------------------------------------------------

    scrollToBottom();

}

// ==========================================================
// AUTO SCROLL
// ==========================================================

function scrollToBottom() {

    messages.scrollTop = messages.scrollHeight;

}

// ==========================================================
// LOAD CHAT HISTORY
// ==========================================================

async function loadHistory() {

    try {

        const response = await fetch("/ai/history");

        if (!response.ok) {

            throw new Error("Failed to fetch chat history.");

        }

        const data = await response.json();

        messages.innerHTML = "";

        const firstName = data.first_name || "there";

        if (!data.messages || data.messages.length === 0) {

            appendMessage(

                "FOCOST AI",

                `Hello **${firstName}** 👋
                **_I'm your financial coach._**
                How can I help you with your finances today?`,

                "assistant"

            );

            scrollToBottom();

            return;

        }

        data.messages.forEach(msg => {

            appendMessage(

                msg.sender,

                msg.message,

                msg.role

            );

        });

        scrollToBottom();

    }

    catch (err) {

        console.error("Failed to load chat history:", err);

        messages.innerHTML = "";

        appendMessage(

            "FOCOST AI",

            "Sorry, I couldn't load your previous conversation. Please try again later.",

            "assistant"

        );

    }

}

// ==========================================================
// SEND MESSAGE
// ==========================================================

async function sendMessage() {

    const question = input.value.trim();

    if (!question)
        return;

    appendMessage(

        "You",

        question,

        "user"

    );

    input.value = "";

    showTyping();

    try {

        const response = await fetch(

            "/ai/chat",

            {

                method: "POST",

                headers: {

                    "Content-Type": "application/json",
                    "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || ""

                },

                body: JSON.stringify({

                    message: question

                })

            }

        );

        const data = await response.json();

        removeTyping();

        if (data.success) {

            appendMessage(
                "FOCOST AI",
                data.message,
                "assistant"
            );

        } else {

            appendMessage(
                "FOCOST AI",
                data.message || "Something went wrong.",
                "assistant"
            );

        }

    }

    catch {

        removeTyping();

        appendMessage(

            "FOCOST AI",

            "Unable to reach AI service (Retry later).",

            "assistant"

        );

    }

}

// ==========================================================
// TYPING INDICATOR
// ==========================================================

function showTyping() {

    removeTyping();

    const div = document.createElement("div");

    div.id = "typingIndicator";

    div.className = "ai-message";

    div.innerHTML =

        "<strong>FOCOST AI</strong><br>Typing...";

    messages.appendChild(div);

    scrollToBottom();

}

function removeTyping() {

    const div = document.getElementById(

        "typingIndicator"

    );

    if (div)

        div.remove();

}

sendBtn.addEventListener("click", sendMessage);

input.addEventListener(

    "keydown",

    function (e) {

        if (

            e.key === "Enter"

            &&

            !e.shiftKey

        ) {

            e.preventDefault();

            sendMessage();

        }

    }

);

// ==========================================================
// BUTTON EVENTS
// ==========================================================

aiButton.addEventListener(

    "click",

    function () {

        if (aiWindow.style.display === "flex") {

            closeWindow();

        }

        else {

            openWindow();

        }

    }

);

minimizeBtn.addEventListener(

    "click",

    function () {

        if (isMinimized) {

            restoreWindow();

        }

        else {

            minimizeWindow();

        }

    }

);

closeBtn.addEventListener(

    "click",

    function () {

        closeWindow();

    }

);

maximizeBtn.addEventListener(

    "click",

    function () {

        if (isMaximized) {

            restoreMaximizedWindow();

        }

        else {

            maximizeWindow();

        }

    }

);

// ==========================================================
// SAVE WINDOW SIZE
// ==========================================================

window.addEventListener("mouseup", function () {

    localStorage.setItem(

        "ai_width",

        aiWindow.offsetWidth + "px"

    );

    localStorage.setItem(

        "ai_height",

        aiWindow.offsetHeight + "px"

    );

});

// Load previous conversation

loadHistory();

// Restore window state after page navigation

if (

    localStorage.getItem("ai_display") === "open"

) {

    aiWindow.style.display = "flex";

}

window.addEventListener("resize", () => {

    if(window.innerWidth <= 767){

        aiWindow.style.left = "";
        aiWindow.style.top = "";

        aiWindow.style.right = "10px";
        aiWindow.style.bottom = "80px";

    }

});