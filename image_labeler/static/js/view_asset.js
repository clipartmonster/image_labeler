function reloadWithAssetId() {
    let assetId = document.getElementById("assetSearch").value.trim();
    if (assetId) {
        let currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set("asset_id", assetId); // Update query parameter
        window.location.href = currentUrl.toString(); // Reload with new URL
    }
}