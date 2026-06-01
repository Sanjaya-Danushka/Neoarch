"""Bundle operations mixin for the main window."""

from neoarch.backend.services import bundle as bundle_service


class _BundlesMixin:
    def go_to_bundles(self):
        """Switch to bundles view"""
        self.switch_view("bundles")

    def add_selected_to_bundle(self):
        return bundle_service.add_selected_to_bundle(self)

    def refresh_bundles_table(self):
        return bundle_service.refresh_bundles_table(self)

    def export_bundle(self):
        return bundle_service.export_bundle(self)

    def import_bundle(self):
        return bundle_service.import_bundle(self)

    def remove_selected_from_bundle(self):
        return bundle_service.remove_selected_from_bundle(self)

    def clear_bundle(self):
        return bundle_service.clear_bundle(self)

    def install_bundle(self):
        return bundle_service.install_bundle(self)

    def add_selected_to_community(self):
        return bundle_service.add_selected_to_community(self)
