// Function to fetch SSH session data from the Flask server
function fetchSSH_Sessions() {
    fetch('http://127.0.0.1:5000/ssh_sessions')
        .then(response => response.json())
        .then(data => {
            displaySSHSessions(data);
        })
        .catch(error => {
            console.error('Error fetching SSH sessions:', error);
        });
}

// Function to fetch shelLM sessions data from the Flask server
function fetchShelLM_Sessions() {
    fetch('http://127.0.0.1:5000/shellm_sessions')
        .then(response => response.json())
        .then(data => {
            displayshelLMSessions(data);
        })
        .catch(error => {
            console.error('Error fetching shelLM sessions:', error);
        });
}

// Function to fetch Commands data from the Flask server
function fetchCommands() {
    fetch('http://127.0.0.1:5000/commands')
        .then(response => response.json())
        .then(data => {
            displayCommands(data);
        })
        .catch(error => {
            console.error('Error fetching Commands:', error);
        });
}

// Function to fetch Answers data from the Flask server
function fetchAnswers() {
    fetch('http://127.0.0.1:5000/answers')
        .then(response => response.json())
        .then(data => {
            displayAnswers(data);
        })
        .catch(error => {
            console.error('Error fetching Answers:', error);
        });
}

// Function to display SSH sessions in the table
function displaySSHSessions(sessions) {
    console.log("Sessions data received:", sessions);

    const table = document.getElementById("ssh-sessions-table"); // Reference to the table
    const tableBody = document.getElementById("ssh-sessions-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'ssh-sessions-table' or 'ssh-sessions-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";  // Unhide the table

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'sessions' is an array and contains valid data
    if (Array.isArray(sessions) && sessions.length > 0) {
        sessions.forEach((session, index) => {
            console.log(`Processing session ${index}:`, session);

            // 检查是否为字典格式的数据
            if (typeof session === 'object' && session !== null && !Array.isArray(session)) {
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session.id;

                const usernameCell = document.createElement("td");
                usernameCell.textContent = session.username;

                const timeDateCell = document.createElement("td");
                timeDateCell.textContent = session.time_date;

                const srcIPCell = document.createElement("td");
                srcIPCell.textContent = session.src_ip;

                const dstIPCell = document.createElement("td");
                dstIPCell.textContent = session.dst_ip;

                const dstPortCell = document.createElement("td");
                dstPortCell.textContent = session.dst_port;

                row.appendChild(idCell);
                row.appendChild(usernameCell);
                row.appendChild(timeDateCell);
                row.appendChild(srcIPCell);
                row.appendChild(dstIPCell);
                row.appendChild(dstPortCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(session) && session.length >= 7) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session[0];

                const usernameCell = document.createElement("td");
                usernameCell.textContent = session[1];

                const timeDateCell = document.createElement("td");
                timeDateCell.textContent = session[2];

                const srcIPCell = document.createElement("td");
                srcIPCell.textContent = session[3];

                const dstIPCell = document.createElement("td");
                dstIPCell.textContent = session[4];

                const dstPortCell = document.createElement("td");
                dstPortCell.textContent = session[6];

                row.appendChild(idCell);
                row.appendChild(usernameCell);
                row.appendChild(timeDateCell);
                row.appendChild(srcIPCell);
                row.appendChild(dstIPCell);
                row.appendChild(dstPortCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid session data:", session);
            }
        });

        console.log("Table populated successfully.");
    } else {
        console.error("Invalid data structure received:", sessions);
    }
}


// Function to display SSH sessions in the table
function displayshelLMSessions(sessions) {
    console.log("Sessions data received:", sessions);

    const table = document.getElementById("shellm-sessions-table"); // Reference to the table
    const tableBody = document.getElementById("shellm-sessions-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'shellm-sessions-table' or 'shellm-sessions-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";  // Unhide the table

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'sessions' is an array and contains valid data
    if (Array.isArray(sessions) && sessions.length > 0) {
        sessions.forEach((session, index) => {
            console.log(`Processing session ${index}:`, session);

            // 检查是否为字典格式的数据
            if (typeof session === 'object' && session !== null && !Array.isArray(session)) {
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session.id;
                idCell.style.cursor = "pointer";
                idCell.addEventListener("click", () => fetchAndDisplayCommandsAnswers(session.id));

                const ssh_session_idCell = document.createElement("td");
                ssh_session_idCell.textContent = session.ssh_session_id;

                const modelCell = document.createElement("td");
                modelCell.textContent = session.model;

                const start_timeCell = document.createElement("td");
                start_timeCell.textContent = session.start_time;

                const end_timeCell = document.createElement("td");
                end_timeCell.textContent = session.end_time;

                const attacker_idCell = document.createElement("td");
                attacker_idCell.textContent = session.attacker_id;

                row.appendChild(idCell);
                row.appendChild(ssh_session_idCell);
                row.appendChild(modelCell);
                row.appendChild(start_timeCell);
                row.appendChild(end_timeCell);
                row.appendChild(attacker_idCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(session) && session.length >= 6) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session[0];
                idCell.style.cursor = "pointer";
                idCell.addEventListener("click", () => fetchAndDisplayCommandsAnswers(session[0]));

                const ssh_session_idCell = document.createElement("td");
                ssh_session_idCell.textContent = session[1];

                const modelCell = document.createElement("td");
                modelCell.textContent = session[2];

                const start_timeCell = document.createElement("td");
                start_timeCell.textContent = session[3];

                const end_timeCell = document.createElement("td");
                end_timeCell.textContent = session[4];

                const attacker_idCell = document.createElement("td");
                attacker_idCell.textContent = session[5];

                row.appendChild(idCell);
                row.appendChild(ssh_session_idCell);
                row.appendChild(modelCell);
                row.appendChild(start_timeCell);
                row.appendChild(end_timeCell);
                row.appendChild(attacker_idCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid session data:", session);
            }
        });

        console.log("Table populated successfully.");
    } else {
        console.error("Invalid data structure received:", sessions);
    }
}

// Function to display SSH sessions in the table
function displayCommands(sessions) {
    console.log("Commands data received:", sessions);

    const table = document.getElementById("commands-table"); // Reference to the table
    const tableBody = document.getElementById("commands-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'commands-table' or 'commands-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";  // Unhide the table

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'sessions' is an array and contains valid data
    if (Array.isArray(sessions) && sessions.length > 0) {
        sessions.forEach((session, index) => {
            console.log(`Processing command ${index}:`, session);

            // 检查是否为字典格式的数据
            if (typeof session === 'object' && session !== null && !Array.isArray(session)) {
                const row = document.createElement("tr");

                const command_idCell = document.createElement("td");
                command_idCell.textContent = session.command_id;

                const shellm_session_idCell = document.createElement("td");
                shellm_session_idCell.textContent = session.shellm_session_id;

                const commandCell = document.createElement("td");
                commandCell.textContent = session.command;

                row.appendChild(command_idCell);
                row.appendChild(shellm_session_idCell);
                row.appendChild(commandCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(session) && session.length >= 3) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const command_idCell = document.createElement("td");
                command_idCell.textContent = session[0];

                const shellm_session_idCell = document.createElement("td");
                shellm_session_idCell.textContent = session[1];

                const commandCell = document.createElement("td");
                commandCell.textContent = session[2];

                row.appendChild(command_idCell);
                row.appendChild(shellm_session_idCell);
                row.appendChild(commandCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid command data:", session);
            }
        });

        console.log("Table populated successfully.");
    } else {
        console.error("Invalid data structure received:", sessions);
    }
}

// Function to display SSH sessions in the table
function displayAnswers(sessions) {
    console.log("Answers data received:", sessions);

    const table = document.getElementById("answers-table"); // Reference to the table
    const tableBody = document.getElementById("answers-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'answers-table' or 'answers-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";  // Unhide the table

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'sessions' is an array and contains valid data
    if (Array.isArray(sessions) && sessions.length > 0) {
        sessions.forEach((session, index) => {
            console.log(`Processing answer ${index}:`, session);

            // 检查是否为字典格式的数据
            if (typeof session === 'object' && session !== null && !Array.isArray(session)) {
                const row = document.createElement("tr");

                const answer_idCell = document.createElement("td");
                answer_idCell.textContent = session.answer_id;

                const command_idCell = document.createElement("td");
                command_idCell.textContent = session.command_id;

                const answerCell = document.createElement("td");
                answerCell.textContent = session.answer;

                row.appendChild(answer_idCell);
                row.appendChild(command_idCell);
                row.appendChild(answerCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(session) && session.length >= 3) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const answer_idCell = document.createElement("td");
                answer_idCell.textContent = session[0];

                const command_idCell = document.createElement("td");
                command_idCell.textContent = session[1];

                const answerCell = document.createElement("td");
                answerCell.textContent = session[2];

                row.appendChild(answer_idCell);
                row.appendChild(command_idCell);
                row.appendChild(answerCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid answer data:", session);
            }
        });

        console.log("Table populated successfully.");
    } else {
        console.error("Invalid data structure received:", sessions);
    }
}

// Function to fetch and display commands and answers for a shellm session
function fetchAndDisplayCommandsAnswers(shellmSessionID) {
    console.log("Fetching commands and answers for ShellM Session ID:", shellmSessionID);

    fetch(`http://127.0.0.1:5000/commands_answers/${shellmSessionID}`)
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then((data) => {
            const tableBody = document.getElementById("commands-answers-table-body");
            const commandsAnswersTable = document.getElementById("commands-answers-table");

            if (!tableBody || !commandsAnswersTable) {
                console.error("Commands and Answers table elements not found in the DOM.");
                return;
            }

            // Clear previous entries
            tableBody.innerHTML = "";

            // Show the table
            commandsAnswersTable.style.display = "table";

            // Populate the table with the received data
            if (Array.isArray(data) && data.length > 0) {
                data.forEach((entry) => {
                    const row = document.createElement("tr");

                    // Create and populate cells
                    const commandIDCell = document.createElement("td");
                    commandIDCell.textContent = entry.command_id || "N/A";

                    const commandCell = document.createElement("td");
                    commandCell.textContent = entry.command || "N/A";

                    const answerIDCell = document.createElement("td");
                    answerIDCell.textContent = entry.answer_id || "N/A";

                    const answerCell = document.createElement("td");
                    answerCell.textContent = entry.answer || "N/A";

                    // Append cells to the row
                    row.appendChild(commandIDCell);
                    row.appendChild(commandCell);
                    row.appendChild(answerIDCell);
                    row.appendChild(answerCell);

                    // Append the row to the table body
                    tableBody.appendChild(row);
                });
            } else {
                // If no data is found, show a "No data available" message
                const row = document.createElement("tr");
                const noDataCell = document.createElement("td");
                noDataCell.textContent = "No commands or answers found for this session.";
                noDataCell.colSpan = 4;
                row.appendChild(noDataCell);
                tableBody.appendChild(row);
            }
        })
        .catch((error) => console.error("Error fetching commands and answers:", error));
}

// Function to hide all tables
function hideAllTables() {
    const tables = document.querySelectorAll('table');
    tables.forEach(table => table.style.display = 'none');
}

// Add event listeners to the buttons
document.getElementById('sshSessionsBtn').addEventListener('click', () => {
    hideAllTables();
    fetchSSH_Sessions();
});
document.getElementById('shelLM_SessionsBtn').addEventListener('click', () => {
    hideAllTables();
    fetchShelLM_Sessions();
});
document.getElementById('commandsBtn').addEventListener('click', () => {
    hideAllTables();
    fetchCommands();
});
document.getElementById('answersBtn').addEventListener('click', () => {
    hideAllTables();
    fetchAnswers();
});

// Function to handle ID click
function handleIDClick(shellmSessionID) {
    console.log("ShellM Session ID clicked:", shellmSessionID);

    const commandsAnswersSection = document.getElementById("commands-answers-section");
    commandsAnswersSection.style.display = "block"; // Show the new button

    const commandsAnswersBtn = document.getElementById("commandsAnswersBtn");
    commandsAnswersBtn.onclick = () => fetchAndDisplayCommandsAnswers(shellmSessionID); // Attach handler
}

// Ensure the page is ready for actions
document.addEventListener("DOMContentLoaded", () => {
    console.log("Log Manager Dashboard ready.");
});

// POP3 Sessions
function fetchPOP3Sessions() {
    fetch('http://127.0.0.1:5000/pop3_sessions')
        .then(response => response.json())
        .then(data => {
            displayPOP3Sessions(data);
        })
        .catch(error => {
            console.error('Error fetching POP3 sessions:', error);
        });
}
function displayPOP3Sessions(sessions) {
    console.log("POP3 sessions data received:", sessions);

    const table = document.getElementById("pop3-sessions-table");
    const tableBody = document.getElementById("pop3-sessions-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'pop3-sessions-table' or 'pop3-sessions-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'sessions' is an array and contains valid data
    if (Array.isArray(sessions) && sessions.length > 0) {
        sessions.forEach((session, index) => {
            console.log(`Processing POP3 session ${index}:`, session);

            // 检查是否为字典格式的数据
            if (typeof session === 'object' && session !== null && !Array.isArray(session)) {
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session.id;
                idCell.style.cursor = "pointer";
                idCell.addEventListener("click", () => fetchAndDisplayPOP3Commands(session.id));

                const usernameCell = document.createElement("td");
                usernameCell.textContent = session.username;

                const timeDateCell = document.createElement("td");
                timeDateCell.textContent = session.time_date;

                const srcIPCell = document.createElement("td");
                srcIPCell.textContent = session.src_ip;

                const dstIPCell = document.createElement("td");
                dstIPCell.textContent = session.dst_ip;

                const srcPortCell = document.createElement("td");
                srcPortCell.textContent = session.src_port;

                const dstPortCell = document.createElement("td");
                dstPortCell.textContent = session.dst_port;

                row.appendChild(idCell);
                row.appendChild(usernameCell);
                row.appendChild(timeDateCell);
                row.appendChild(srcIPCell);
                row.appendChild(dstIPCell);
                row.appendChild(srcPortCell);
                row.appendChild(dstPortCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(session) && session.length >= 7) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session[0];
                idCell.style.cursor = "pointer";
                idCell.addEventListener("click", () => fetchAndDisplayPOP3Commands(session[0]));

                const usernameCell = document.createElement("td");
                usernameCell.textContent = session[1];

                const timeDateCell = document.createElement("td");
                timeDateCell.textContent = session[2];

                const srcIPCell = document.createElement("td");
                srcIPCell.textContent = session[3];

                const dstIPCell = document.createElement("td");
                dstIPCell.textContent = session[4];

                const srcPortCell = document.createElement("td");
                srcPortCell.textContent = session[5];

                const dstPortCell = document.createElement("td");
                dstPortCell.textContent = session[6];

                row.appendChild(idCell);
                row.appendChild(usernameCell);
                row.appendChild(timeDateCell);
                row.appendChild(srcIPCell);
                row.appendChild(dstIPCell);
                row.appendChild(srcPortCell);
                row.appendChild(dstPortCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid POP3 session data:", session);
            }
        });

        console.log("POP3 sessions table populated successfully.");
    } else {
        console.error("Invalid POP3 sessions data structure received:", sessions);
    }
}
function fetchAndDisplayPOP3Commands(sessionID) {
    fetch(`http://127.0.0.1:5000/pop3_commands/${sessionID}`)
        .then(response => response.json())
        .then(data => {
            displayPOP3Commands(data);
        })
        .catch(error => {
            console.error('Error fetching POP3 commands:', error);
        });
}
function displayPOP3Commands(commands) {
    console.log("POP3 commands data received:", commands);

    const table = document.getElementById("pop3-commands-table");
    const tableBody = document.getElementById("pop3-commands-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'pop3-commands-table' or 'pop3-commands-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'commands' is an array and contains valid data
    if (Array.isArray(commands) && commands.length > 0) {
        commands.forEach((command, index) => {
            console.log(`Processing POP3 command ${index}:`, command);

            // 检查是否为字典格式的数据
            if (typeof command === 'object' && command !== null && !Array.isArray(command)) {
                const row = document.createElement("tr");

                const command_idCell = document.createElement("td");
                command_idCell.textContent = command.command_id;

                const pop3_session_idCell = document.createElement("td");
                pop3_session_idCell.textContent = command.pop3_session_id;

                const commandCell = document.createElement("td");
                commandCell.textContent = command.command;

                const responseCell = document.createElement("td");
                responseCell.textContent = command.response;

                const timestampCell = document.createElement("td");
                timestampCell.textContent = command.timestamp;

                row.appendChild(command_idCell);
                row.appendChild(pop3_session_idCell);
                row.appendChild(commandCell);
                row.appendChild(responseCell);
                row.appendChild(timestampCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(command) && command.length >= 5) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const command_idCell = document.createElement("td");
                command_idCell.textContent = command[0];

                const pop3_session_idCell = document.createElement("td");
                pop3_session_idCell.textContent = command[1];

                const commandCell = document.createElement("td");
                commandCell.textContent = command[2];

                const responseCell = document.createElement("td");
                responseCell.textContent = command[3];

                const timestampCell = document.createElement("td");
                timestampCell.textContent = command[4];

                row.appendChild(command_idCell);
                row.appendChild(pop3_session_idCell);
                row.appendChild(commandCell);
                row.appendChild(responseCell);
                row.appendChild(timestampCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid POP3 command data:", command);
            }
        });

        console.log("POP3 commands table populated successfully.");
    } else {
        console.error("Invalid POP3 commands data structure received:", commands);
    }
}
// HTTP Sessions
function fetchHTTPSessions() {
    fetch('http://127.0.0.1:5000/http_sessions')
        .then(response => response.json())
        .then(data => {
            displayHTTPSessions(data);
        })
        .catch(error => {
            console.error('Error fetching HTTP sessions:', error);
        });
}
function displayHTTPSessions(sessions) {
    hideAllTables();
    const table = document.getElementById("http-sessions-table");
    const tableBody = document.getElementById("http-sessions-table-body");
    table.style.display = "table";
    tableBody.innerHTML = "";
    if (Array.isArray(sessions) && sessions.length > 0) {
        sessions.forEach((session, index) => {
            const row = document.createElement("tr");
            for (let i = 0; i < 4; i++) {
                const cell = document.createElement("td");
                cell.textContent = session[i];
                if (i === 0) {
                    cell.style.cursor = "pointer";
                    cell.addEventListener("click", () => fetchAndDisplayHTTPRequests(session[0]));
                }
                row.appendChild(cell);
            }
            tableBody.appendChild(row);
        });
    }
}
function fetchAndDisplayHTTPRequests(sessionID) {
    fetch(`http://127.0.0.1:5000/http_requests/${sessionID}`)
        .then(response => response.json())
        .then(data => {
            displayHTTPRequests(data);
        })
        .catch(error => {
            console.error('Error fetching HTTP requests:', error);
        });
}
function displayHTTPRequests(requests) {
    console.log("HTTP requests data received:", requests);

    const table = document.getElementById("http-requests-table");
    const tableBody = document.getElementById("http-requests-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'http-requests-table' or 'http-requests-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'requests' is an array and contains valid data
    if (Array.isArray(requests) && requests.length > 0) {
        requests.forEach((request, index) => {
            console.log(`Processing request ${index}:`, request);

            if (!Array.isArray(request) || request.length < 7) {
                console.error("Invalid request data:", request);
                return;
            }

            const row = document.createElement("tr");

            const request_idCell = document.createElement("td");
            request_idCell.textContent = request[0];

            const http_session_idCell = document.createElement("td");
            http_session_idCell.textContent = request[1];

            const methodCell = document.createElement("td");
            methodCell.textContent = request[2];

            const pathCell = document.createElement("td");
            pathCell.textContent = request[3];

            const headersCell = document.createElement("td");
            headersCell.textContent = request[4];

            const request_timeCell = document.createElement("td");
            request_timeCell.textContent = request[5];

            const responseCell = document.createElement("td");
            responseCell.textContent = request[6];

            row.appendChild(request_idCell);
            row.appendChild(http_session_idCell);
            row.appendChild(methodCell);
            row.appendChild(pathCell);
            row.appendChild(headersCell);
            row.appendChild(request_timeCell);
            row.appendChild(responseCell);

            tableBody.appendChild(row);
        });

        console.log("Table populated successfully.");
    } else {
        console.error("Invalid data structure received:", requests);
    }
}
// 按钮事件绑定
window.onload = function() {
    document.getElementById("sshSessionsBtn").onclick = fetchSSH_Sessions;
    document.getElementById("shelLM_SessionsBtn").onclick = fetchShelLM_Sessions;
    document.getElementById("commandsBtn").onclick = fetchCommands;
    document.getElementById("answersBtn").onclick = fetchAnswers;
    document.getElementById("pop3SessionsBtn").onclick = fetchPOP3Sessions;
    document.getElementById("httpSessionsBtn").onclick = fetchHTTPSessions;
};

// MySQL相关函数
function fetchMySQLSessions() {
    fetch('http://127.0.0.1:5000/mysql_sessions')
        .then(response => response.json())
        .then(data => {
            displayMySQLSessions(data);
        })
        .catch(error => {
            console.error('Error fetching MySQL sessions:', error);
        });
}

function displayMySQLSessions(sessions) {
    console.log("MySQL sessions data received:", sessions);

    const table = document.getElementById("mysql-sessions-table");
    const tableBody = document.getElementById("mysql-sessions-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'mysql-sessions-table' or 'mysql-sessions-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'sessions' is an array and contains valid data
    if (Array.isArray(sessions) && sessions.length > 0) {
        sessions.forEach((session, index) => {
            console.log(`Processing MySQL session ${index}:`, session);

            // 检查是否为字典格式的数据
            if (typeof session === 'object' && session !== null && !Array.isArray(session)) {
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session.id;
                idCell.style.cursor = "pointer";
                idCell.addEventListener("click", () => fetchAndDisplayMySQLCommands(session.id));

                const usernameCell = document.createElement("td");
                usernameCell.textContent = session.username;

                const timeDateCell = document.createElement("td");
                timeDateCell.textContent = session.time_date;

                const srcIPCell = document.createElement("td");
                srcIPCell.textContent = session.src_ip;

                const dstIPCell = document.createElement("td");
                dstIPCell.textContent = session.dst_ip;

                const srcPortCell = document.createElement("td");
                srcPortCell.textContent = session.src_port;

                const dstPortCell = document.createElement("td");
                dstPortCell.textContent = session.dst_port;

                const databaseNameCell = document.createElement("td");
                databaseNameCell.textContent = session.database_name || '';

                row.appendChild(idCell);
                row.appendChild(usernameCell);
                row.appendChild(timeDateCell);
                row.appendChild(srcIPCell);
                row.appendChild(dstIPCell);
                row.appendChild(srcPortCell);
                row.appendChild(dstPortCell);
                row.appendChild(databaseNameCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(session) && session.length >= 8) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const idCell = document.createElement("td");
                idCell.textContent = session[0];
                idCell.style.cursor = "pointer";
                idCell.addEventListener("click", () => fetchAndDisplayMySQLCommands(session[0]));

                const usernameCell = document.createElement("td");
                usernameCell.textContent = session[1];

                const timeDateCell = document.createElement("td");
                timeDateCell.textContent = session[2];

                const srcIPCell = document.createElement("td");
                srcIPCell.textContent = session[3];

                const dstIPCell = document.createElement("td");
                dstIPCell.textContent = session[4];

                const srcPortCell = document.createElement("td");
                srcPortCell.textContent = session[5];

                const dstPortCell = document.createElement("td");
                dstPortCell.textContent = session[6];

                const databaseNameCell = document.createElement("td");
                databaseNameCell.textContent = session[7] || '';

                row.appendChild(idCell);
                row.appendChild(usernameCell);
                row.appendChild(timeDateCell);
                row.appendChild(srcIPCell);
                row.appendChild(dstIPCell);
                row.appendChild(srcPortCell);
                row.appendChild(dstPortCell);
                row.appendChild(databaseNameCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid MySQL session data:", session);
            }
        });

        console.log("MySQL sessions table populated successfully.");
    } else {
        console.error("Invalid MySQL sessions data structure received:", sessions);
    }
}

function fetchAndDisplayMySQLCommands(sessionID) {
    fetch(`http://127.0.0.1:5000/mysql_commands/${sessionID}`)
        .then(response => response.json())
        .then(data => {
            displayMySQLCommands(data);
        })
        .catch(error => {
            console.error('Error fetching MySQL commands:', error);
        });
}

function displayMySQLCommands(commands) {
    console.log("MySQL commands data received:", commands);

    const table = document.getElementById("mysql-commands-table");
    const tableBody = document.getElementById("mysql-commands-table-body");

    if (!table || !tableBody) {
        console.error("Table or table body with ID 'mysql-commands-table' or 'mysql-commands-table-body' not found.");
        return;
    }

    // Make sure the table is visible
    table.style.display = "table";

    // Clear previous entries
    tableBody.innerHTML = "";

    // Check if 'commands' is an array and contains valid data
    if (Array.isArray(commands) && commands.length > 0) {
        commands.forEach((command, index) => {
            console.log(`Processing MySQL command ${index}:`, command);

            // 检查是否为字典格式的数据
            if (typeof command === 'object' && command !== null && !Array.isArray(command)) {
                const row = document.createElement("tr");

                const command_idCell = document.createElement("td");
                command_idCell.textContent = command.command_id;

                const mysql_session_idCell = document.createElement("td");
                mysql_session_idCell.textContent = command.mysql_session_id;

                const commandCell = document.createElement("td");
                commandCell.textContent = command.command;

                const responseCell = document.createElement("td");
                responseCell.textContent = command.response;

                const timestampCell = document.createElement("td");
                timestampCell.textContent = command.timestamp;

                const commandTypeCell = document.createElement("td");
                commandTypeCell.textContent = command.command_type || '';

                const affectedRowsCell = document.createElement("td");
                affectedRowsCell.textContent = command.affected_rows || 0;

                row.appendChild(command_idCell);
                row.appendChild(mysql_session_idCell);
                row.appendChild(commandCell);
                row.appendChild(responseCell);
                row.appendChild(timestampCell);
                row.appendChild(commandTypeCell);
                row.appendChild(affectedRowsCell);

                tableBody.appendChild(row);
            } else if (Array.isArray(command) && command.length >= 7) {
                // 保持对数组格式的兼容性
                const row = document.createElement("tr");

                const command_idCell = document.createElement("td");
                command_idCell.textContent = command[0];

                const mysql_session_idCell = document.createElement("td");
                mysql_session_idCell.textContent = command[1];

                const commandCell = document.createElement("td");
                commandCell.textContent = command[2];

                const responseCell = document.createElement("td");
                responseCell.textContent = command[3];

                const timestampCell = document.createElement("td");
                timestampCell.textContent = command[4];

                const commandTypeCell = document.createElement("td");
                commandTypeCell.textContent = command[5] || '';

                const affectedRowsCell = document.createElement("td");
                affectedRowsCell.textContent = command[6] || 0;

                row.appendChild(command_idCell);
                row.appendChild(mysql_session_idCell);
                row.appendChild(commandCell);
                row.appendChild(responseCell);
                row.appendChild(timestampCell);
                row.appendChild(commandTypeCell);
                row.appendChild(affectedRowsCell);

                tableBody.appendChild(row);
            } else {
                console.error("Invalid MySQL command data:", command);
            }
        });

        console.log("MySQL commands table populated successfully.");
    } else {
        console.error("Invalid MySQL commands data structure received:", commands);
    }
}

// 更新hideAllTables函数以包含MySQL表格
function hideAllTables() {
    const tables = [
        "ssh-sessions-table",
        "shellm-sessions-table",
        "commands-table",
        "answers-table",
        "commands-answers-table",
        "pop3-sessions-table",
        "pop3-commands-table",
        "http-sessions-table",
        "http-requests-table",
        "mysql-sessions-table",
        "mysql-commands-table"
    ];

    tables.forEach(tableId => {
        const table = document.getElementById(tableId);
        if (table) {
            table.style.display = "none";
        }
    });
}

// 添加事件监听器
document.addEventListener('DOMContentLoaded', function() {
    // 现有的按钮事件监听器
    document.getElementById('sshSessionsBtn').addEventListener('click', function() {
        hideAllTables();
        fetchSSH_Sessions();
    });

    document.getElementById('shelLM_SessionsBtn').addEventListener('click', function() {
        hideAllTables();
        fetchShelLM_Sessions();
    });

    document.getElementById('commandsBtn').addEventListener('click', function() {
        hideAllTables();
        fetchCommands();
    });

    document.getElementById('answersBtn').addEventListener('click', function() {
        hideAllTables();
        fetchAnswers();
    });

    document.getElementById('pop3SessionsBtn').addEventListener('click', function() {
        hideAllTables();
        fetchPOP3Sessions();
    });

    document.getElementById('httpSessionsBtn').addEventListener('click', function() {
        hideAllTables();
        fetchHTTPSessions();
    });

    // 添加MySQL按钮事件监听器
    document.getElementById('mysqlSessionsBtn').addEventListener('click', function() {
        hideAllTables();
        fetchMySQLSessions();
    });
});
