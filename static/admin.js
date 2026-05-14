const appDiv = document.getElementById('app');

// 1. Fetch Admin Data from Python
async function loadAdminPanel() {
    appDiv.innerHTML = '<i>Loading admin data...</i>';
    
    const response = await fetch('/api/admin_data');
    if (!response.ok) return window.location.href = '/'; // Kick out if not admin
    const data = await response.json();

    buildUI(data.invites);
}

// 2. Build the UI using only JavaScript
function buildUI(invites) {
    appDiv.innerHTML = ''; // Clear loading text

    // Title
    const title = document.createElement('h2');
    title.textContent = 'Pi Admin Panel';
    appDiv.appendChild(title);

    // --- Generate Invite Section ---
    const generateBtn = document.createElement('button');
    generateBtn.textContent = 'Generate New Invite Code';
    generateBtn.onclick = async () => {
        await fetch('/api/generate_invite', { method: 'POST' });
        loadAdminPanel(); // Refresh the screen
    };
    appDiv.appendChild(generateBtn);

    const activeCodes = document.createElement('p');
    activeCodes.className = 'code-list';
    activeCodes.textContent = 'Active Codes: ' + (invites.join(', ') || 'None');
    appDiv.appendChild(activeCodes);

    appDiv.appendChild(document.createElement('hr'));

    // --- Approve User Section ---
    const approveLabel = document.createElement('label');
    approveLabel.textContent = 'Enter User Confirmation Code:';
    appDiv.appendChild(approveLabel);

    const confirmInput = document.createElement('input');
    confirmInput.placeholder = 'e.g. X8Y2Z1';
    appDiv.appendChild(confirmInput);

    const approveBtn = document.createElement('button');
    approveBtn.textContent = 'Approve Account';
    approveBtn.style.background = '#28a745';
    approveBtn.onclick = async () => {
        const formData = new FormData();
        formData.append('confirm_code', confirmInput.value);
        
        const res = await fetch('/api/approve_user', { method: 'POST', body: formData });
        const result = await res.json();
        alert(result.message); // Show success/error popup
        confirmInput.value = ''; // clear input
    };
    appDiv.appendChild(approveBtn);
}

// Boot up the app
loadAdminPanel();
