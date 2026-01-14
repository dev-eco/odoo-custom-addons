/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

/**
 * Calculadora de información de pago
 * Funcionalidades futuras para cálculos dinámicos
 */
class PaymentCalculator extends Component {
    
    /**
     * Calcular descuento por pronto pago
     */
    calculateEarlyDiscount(amount, rate, days) {
        const discount = amount * (rate / 100);
        const finalAmount = amount - discount;
        
        return {
            discount: discount,
            finalAmount: finalAmount,
            dueDate: this.addDays(new Date(), days)
        };
    }
    
    /**
     * Agregar días a una fecha
     */
    addDays(date, days) {
        const result = new Date(date);
        result.setDate(result.getDate() + days);
        return result;
    }
    
    /**
     * Formatear referencia de pago
     */
    formatPaymentReference(template, orderName) {
        return template.replace('{name}', orderName);
    }
    
    /**
     * Validar IBAN
     */
    validateIBAN(iban) {
        // Implementación básica de validación IBAN
        const cleanIban = iban.replace(/\s/g, '').toUpperCase();
        
        if (cleanIban.length < 15 || cleanIban.length > 34) {
            return false;
        }
        
        // Más validaciones pueden agregarse aquí
        return true;
    }
}

// Registrar el componente para uso futuro
registry.category("components").add("PaymentCalculator", PaymentCalculator);

// Funciones utilitarias globales
window.PaymentUtils = {
    calculateEarlyDiscount: (amount, rate, days) => {
        const calculator = new PaymentCalculator();
        return calculator.calculateEarlyDiscount(amount, rate, days);
    },
    
    formatPaymentReference: (template, orderName) => {
        const calculator = new PaymentCalculator();
        return calculator.formatPaymentReference(template, orderName);
    },
    
    validateIBAN: (iban) => {
        const calculator = new PaymentCalculator();
        return calculator.validateIBAN(iban);
    }
};

console.log('Payment Calculator loaded successfully');
