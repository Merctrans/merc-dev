/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
patch(ListRenderer.prototype, "my_list_view_patch", {
  // Define the patched method here
  setup() {
    console.log("List view started!");
    this._super.apply(this, arguments);

    // Call the new method
    // this.myNewMethod();
  },

  _onClick(record) {
    // Kiểm tra xem record có thuộc model project.task không
    if (record.resModel === 'project.task') {
      const result = confirm("Are you sure you want to delete this POs?");
      
      if (result) {
        this.onDeleteRecord(record);
      } else {
        console.log("Delete operation cancelled");
      }
    } else {
      // Đối với các model khác, xóa trực tiếp không cần confirm
      this.onDeleteRecord(record);
    }
  },
});
