/**
 * EnergyComm — Progressive Enhancement AJAX
 * Intercepta formularios con data-ajax-action y los envía sin recargar página.
 * Con JS desactivado, el formulario funciona normalmente (POST → redirect).
 */
document.addEventListener('DOMContentLoaded', () => {
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

  // Interceptar todos los formularios marcados con data-ajax-action
  document.querySelectorAll('form[data-ajax-action]').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const url = form.dataset.ajaxAction;
      const formData = new FormData(form);

      // Asegurar que el token CSRF va en los datos
      if (!formData.has('csrf_token') && csrfToken) {
        formData.set('csrf_token', csrfToken);
      }

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          body: formData
        });

        let data;
        try {
          data = await resp.json();
        } catch {
          mostrarFlash('Respuesta inesperada del servidor.', 'danger');
          return;
        }

        if (data.success) {
          // Eliminar el elemento más cercano con data-removable
          const removable = form.closest('[data-removable]');
          if (removable) removable.remove();

          if (data.message) mostrarFlash(data.message, 'success');

          // Redirigir si el servidor lo indica
          if (data.redirect) {
            window.location.href = data.redirect;
          }
        } else {
          mostrarFlash(data.error || 'Ha ocurrido un error.', 'danger');
        }
      } catch (err) {
        mostrarFlash('Error de conexión. Inténtalo de nuevo.', 'danger');
      }
    });
  });

  function mostrarFlash(mensaje, categoria) {
    let contenedor = document.querySelector('.flash-container');
    if (!contenedor) {
      contenedor = document.createElement('div');
      contenedor.className = 'flash-container';
      contenedor.setAttribute('aria-live', 'polite');
      const main = document.querySelector('main');
      if (main) main.prepend(contenedor);
    }

    const div = document.createElement('div');
    div.className = `flash flash-${categoria}`;
    div.setAttribute('role', 'alert');
    div.textContent = mensaje;
    contenedor.appendChild(div);

    // Auto-eliminar tras 5 segundos
    setTimeout(() => div.remove(), 5000);
  }
});
