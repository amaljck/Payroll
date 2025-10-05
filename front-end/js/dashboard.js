document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll('.sidebar a');
    const sections = document.querySelectorAll('.tab-content');

    links.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            // Remove "active" class from all links
            links.forEach(l => l.classList.remove('active'));

            // Add "active" class to the clicked link
            this.classList.add('active');

            // Hide all sections
            sections.forEach(section => section.classList.remove('active'));

            // Show the section that matches the href
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);

            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });
});