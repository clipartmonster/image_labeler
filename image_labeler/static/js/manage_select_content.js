if (window.location.pathname === '/label_images/manage_select_content/') {

    document.addEventListener('DOMContentLoaded', function () {

        function setParamAndReload(key, value) {
            var url = new URL(window.location.href);
            if (value === '' || value == null) {
                url.searchParams.delete(key);
            } else {
                url.searchParams.set(key, value);
            }
            window.location.href = url.toString();
        }

        document.querySelectorAll('.option.button.rectangle.label_filter').forEach(function (btn) {
            btn.addEventListener('click', function () {
                setParamAndReload('label_filter', this.getAttribute('data-label-filter'));
            });
        });

        document.querySelectorAll('.option.button.rectangle.batch_filter').forEach(function (btn) {
            btn.addEventListener('click', function () {
                setParamAndReload('batch_id', this.getAttribute('data-batch-id'));
            });
        });

        document.querySelectorAll('.option.button.rectangle.sort_filter').forEach(function (btn) {
            btn.addEventListener('click', function () {
                setParamAndReload('sort_by', this.getAttribute('data-sort-by'));
            });
        });

    });

}
