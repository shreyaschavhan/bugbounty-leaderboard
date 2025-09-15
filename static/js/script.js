function openModal(summary, name, score, time) {
    document.getElementById('modal-title').innerText = `Action by ${name}`;
    document.getElementById('modal-details').innerText = summary;
    document.getElementById('modal-user').innerText = name;
    document.getElementById('modal-score').innerText = `+${score} pts`;
    document.getElementById('modal-time').innerText = `Time: ${time}`;
    document.getElementById('modal').style.display = 'block';
}

document.querySelector('.close').onclick = function() {
    document.getElementById('modal').style.display = 'none';
}

window.onclick = function(event) {
    var modal = document.getElementById('modal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}

// Add keyboard escape functionality
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        document.getElementById('modal').style.display = 'none';
    }
});

// Theme toggle functionality
const themeToggle = document.getElementById('themeToggle');
if (themeToggle) {
    // Initialize theme based on saved preference or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const currentTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    
    document.body.setAttribute('data-theme', currentTheme);
    
    // Update icon based on current theme
    const icon = themeToggle.querySelector('i');
    icon.className = currentTheme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    
    themeToggle.addEventListener('click', () => {
        const currentTheme = document.body.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.body.setAttribute('data-theme', newTheme);
        
        // Update icon
        const icon = themeToggle.querySelector('i');
        icon.className = newTheme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
        
        // Save preference to localStorage
        localStorage.setItem('theme', newTheme);
    });
}

// NEW: Event delegation for action cards
document.body.addEventListener('click', function(event) {
    // Traverse the DOM from the clicked element up to find the action card
    const cardElement = event.target.closest('.action-card-modern');
    if (cardElement) {
        // Extract data from attributes
        const summary = cardElement.dataset.summary;
        const userName = cardElement.dataset.user;
        const score = cardElement.dataset.score;
        const time = cardElement.dataset.time;

        // Call the modal function with the safely extracted data
        openModal(summary, userName, score, time);
    }
});

// NEW: Optional - Add a CSS class to indicate interactivity for better UX
const style = document.createElement('style');
style.textContent = `
    .action-card-modern { cursor: pointer; }
    .action-card-modern:hover { opacity: 0.9; }
`;
document.head.appendChild(style);