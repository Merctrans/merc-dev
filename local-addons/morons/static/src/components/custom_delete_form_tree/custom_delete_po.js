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

    const result = confirm("Are you sure you want to delete this POs?");
    
    // var currentModel = window.location.href.split('/')[3];
    // var params = currentModel.split('&');

    // var modelValue;
    // for (var i = 0; i < params.length; i++) {
    //     var param = params[i].split('=');
    //     if (param[0] === 'model') {
    //         modelValue = param[1];
    //         break;
    //     }
    // }

    // console.log(modelValue);
    
    if (result) {

      this.onDeleteRecord(record);
    } else {

      console.log("Delete operation cancelled");
    }
  },
});

