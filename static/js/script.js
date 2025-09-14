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