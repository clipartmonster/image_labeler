document.addEventListener('DOMContentLoaded', () => {
    const button = document.querySelector('.option.button.rectangle.model_results.control_plots');

    if (button) {
        // Add an event listener to the button
        button.addEventListener('click', control_model_result_plots);
    } else {
        console.error('Button not found in the DOM');
    }
});

function control_model_result_plots() {

    const button = document.querySelector('.option.button.rectangle.model_results.control_plots');
    const buttonText = button.querySelector('h1'); // Select the <h1> inside the button
    
    const plots = document.querySelectorAll('.model_results.plot');

    plots.forEach((plot) => {
        if (plot.classList.contains('visible')) {
            // Hide the image
            plot.style.display = 'none';

            // Change class from 'visible' to 'hidden'
            plot.classList.remove('visible');
            plot.classList.add('hidden');

            buttonText.textContent = 'Show Plots'

        } else if (plot.classList.contains('hidden')) {
            // Show the image if it's hidden and toggle back to 'visible'
            plot.style.display = '';
            plot.classList.remove('hidden');
            plot.classList.add('visible');

            buttonText.textContent = 'Hide Plots'
        }
    });
}
