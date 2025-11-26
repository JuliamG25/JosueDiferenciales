// Configurar MathJax
window.MathJax = {
    tex: {
        inlineMath: [['$', '$'], ['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']],
        processEscapes: true,
        processEnvironments: true
    },
    options: {
        skipHtmlTags: ['script', 'style', 'textarea', 'pre', 'code']
    }
};

let mathJaxProcessed = false;

function renderMath() {
    if (window.MathJax) {
        MathJax.typesetPromise().then(() => {
            mathJaxProcessed = true;
        }).catch((err) => {
            console.log('Error rendering math:', err);
        });
    }
}

// Configurar evento para el botón de resolver
document.addEventListener('DOMContentLoaded', function() {
    const solveBtn = document.getElementById('solve-btn');
    const equationInput = document.getElementById('equation');
    const methodSelect = document.getElementById('method');
    const resultSection = document.getElementById('result-section');
    const solutionDiv = document.getElementById('solution');
    const stepsDiv = document.getElementById('steps');
    const exampleCards = document.querySelectorAll('.example-card');

    // Event listener para el botón resolver
    solveBtn.addEventListener('click', solveEquation);

    // Event listener para Enter en el input
    equationInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            solveEquation();
        }
    });

    // Event listeners para los ejemplos
    exampleCards.forEach(card => {
        card.addEventListener('click', function() {
            const equation = this.getAttribute('data-equation');
            const method = this.getAttribute('data-method');
            
            equationInput.value = equation;
            methodSelect.value = method;
            
            // Resolver automáticamente
            solveEquation();
        });
    });

    function solveEquation() {
        const equation = equationInput.value.trim();
        
        if (!equation) {
            alert('Por favor, ingresa una ecuación diferencial');
            return;
        }

        const method = methodSelect.value;
        const initialConditions = document.getElementById('initial-conditions').value.trim();

        // Mostrar loading
        solveBtn.disabled = true;
        solveBtn.innerHTML = '<span class="loading"></span> Resolviendo...';
        
        resultSection.style.display = 'none';
        solutionDiv.innerHTML = '';
        stepsDiv.innerHTML = '';

        // Hacer petición al servidor
        fetch('/solve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                equation: equation,
                method: method,
                initial_conditions: initialConditions
            })
        })
        .then(response => response.json())
        .then(data => {
            solveBtn.disabled = false;
            solveBtn.textContent = 'Resolver Ecuación';
            
            resultSection.style.display = 'block';
            
            if (data.success && data.solution) {
                // Mostrar solución - usar display math
                let solutionHTML = '';
                
                // Si hay solución general y particular, mostrar ambas
                if (data.general_solution && data.particular_solution && data.general_solution !== data.particular_solution) {
                    solutionHTML += '<div style="margin-bottom: 20px;"><h4 style="color: var(--primary-color); margin-bottom: 10px;">Solución General:</h4>';
                    solutionHTML += `<div style="background: #f0f4f8; padding: 15px; border-radius: 4px; border-left: 3px solid var(--accent-color);">\\[${data.general_solution}\\]</div></div>`;
                    solutionHTML += '<div><h4 style="color: var(--success-color); margin-bottom: 10px;">Solución Particular (con condiciones iniciales):</h4>';
                    solutionHTML += `<div style="background: #eafaf1; padding: 15px; border-radius: 4px; border-left: 3px solid var(--success-color);">\\[${data.particular_solution}\\]</div></div>`;
                } else {
                    // Mostrar solo la solución disponible
                    solutionHTML = `\\[${data.solution}\\]`;
                }
                
                solutionDiv.innerHTML = solutionHTML;
                
                // Mostrar pasos
                stepsDiv.innerHTML = '';
                data.steps.forEach((step, index) => {
                    const stepDiv = document.createElement('div');
                    stepDiv.className = 'step-item';
                    
                    // Procesar LaTeX en el paso
                    // Reemplazar $latex()$ con formato MathJax
                    let processedStep = step.replace(/\$latex\(([^\)]+)\)\$/g, '$$$$$1$$$$');
                    // Reemplazar $$...$$ con \[...\]
                    processedStep = processedStep.replace(/\$\$([^$]+)\$\$/g, '\\[$1\\]');
                    // Reemplazar $...$ con \(...\)
                    processedStep = processedStep.replace(/\$([^$]+)\$/g, '\\($1\\)');
                    
                    stepDiv.innerHTML = processedStep;
                    
                    stepsDiv.appendChild(stepDiv);
                });
                
                // Renderizar MathJax después de agregar contenido
                setTimeout(() => {
                    renderMath();
                }, 100);
            } else {
                // Mostrar error
                solutionDiv.innerHTML = '<div class="error-message">❌ No se pudo resolver la ecuación. Por favor verifica que esté escrita correctamente.</div>';
                
                if (data.steps && data.steps.length > 0) {
                    stepsDiv.innerHTML = '';
                    data.steps.forEach(step => {
                        const stepDiv = document.createElement('div');
                        stepDiv.className = 'step-item';
                        
                        // Procesar LaTeX en el paso
                        let processedStep = step.replace(/\$latex\(([^\)]+)\)\$/g, '$$$$$1$$$$');
                        processedStep = processedStep.replace(/\$\$([^$]+)\$\$/g, '\\[$1\\]');
                        processedStep = processedStep.replace(/\$([^$]+)\$/g, '\\($1\\)');
                        
                        stepDiv.innerHTML = processedStep;
                        stepsDiv.appendChild(stepDiv);
                    });
                    
                    setTimeout(() => {
                        renderMath();
                    }, 100);
                }
            }
        })
        .catch(error => {
            solveBtn.disabled = false;
            solveBtn.textContent = 'Resolver Ecuación';
            
            resultSection.style.display = 'block';
            solutionDiv.innerHTML = `<div class="error-message">❌ Error al comunicarse con el servidor: ${error.message}</div>`;
            console.error('Error:', error);
        });
    }
});

